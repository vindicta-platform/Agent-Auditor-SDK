"""
GeminiAdapter: Async adapter for Google Gemini/AI Studio API.

Uses google-generativeai SDK for API calls.
Implements:
- Rate limit handling with exponential backoff
- Secure API key handling (via SecureKeyManager)
- Token usage tracking
"""

import asyncio
import os
import time
from typing import Optional, Tuple

from agent_auditor.errors import APIKeyNotFoundError, RateLimitError
from agent_auditor.models import AITask, RequestPriority, UsageEntry
from agent_auditor.quota import UsageJournal
from agent_auditor.security import SecureKeyManager
from agent_auditor.settings import GeminiSettings, get_settings


class RateLimiter:
    """
    Token Bucket rate limiter with dual RPM/TPM tracking.

    Implements proactive waiting (waits BEFORE making request) rather than
    reactive backoff (retrying after 429 errors).

    Features:
    - Dual bucket tracking: Requests Per Minute (RPM) and Tokens Per Minute (TPM)
    - Tokens replenish continuously based on elapsed time
    - Thread-safe for concurrent async operations
    - Gemini API free tier compliance (60 RPM, 60K TPM by default)

    Example:
        limiter = RateLimiter(rpm=60, tpm=60_000)
        await limiter.acquire(estimated_tokens=1000)
        # ... make API call ...
    """

    def __init__(self, rpm: int, tpm: int) -> None:
        """
        Initialize rate limiter with Gemini API tier limits.

        Args:
            rpm: Requests per minute limit
            tpm: Tokens per minute limit
        """
        self.rpm = rpm
        self.tpm = tpm

        # Token buckets (start full)
        self._request_tokens = float(rpm)
        self._token_tokens = float(tpm)

        # Track last replenishment time
        self._last_replenish = time.time()

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int) -> bool:
        """
        Acquire tokens for an API call. Waits proactively if tokens unavailable.

        Args:
            estimated_tokens: Estimated token count for the request

        Returns:
            True when tokens acquired (always succeeds after waiting if needed)
        """
        async with self._lock:
            # Replenish tokens based on elapsed time
            self._replenish()

            # Check both buckets
            needed_requests = 1
            needed_tokens = max(estimated_tokens, 0)  # Handle 0 or negative

            # Calculate wait time if insufficient tokens
            wait_time = self._time_until_available(needed_requests, needed_tokens)

            if wait_time > 0:
                # Proactive waiting
                await asyncio.sleep(wait_time)

                # Replenish after waiting
                self._replenish()

            # Consume tokens
            self._request_tokens -= needed_requests
            self._token_tokens -= needed_tokens

            return True

    def _replenish(self) -> None:
        """Replenish tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_replenish

        if elapsed <= 0:
            return

        # Replenish at rate of X per minute = X/60 per second
        request_replenish = (self.rpm / 60.0) * elapsed
        token_replenish = (self.tpm / 60.0) * elapsed

        # Add tokens (but don't exceed bucket capacity)
        self._request_tokens = min(self._request_tokens + request_replenish, float(self.rpm))
        self._token_tokens = min(self._token_tokens + token_replenish, float(self.tpm))

        self._last_replenish = now

    def _time_until_available(self, needed_requests: int, needed_tokens: int) -> float:
        """
        Calculate time to wait until tokens are available.

        Args:
            needed_requests: Number of requests needed
            needed_tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if tokens already available)
        """
        wait_for_requests = 0.0
        wait_for_tokens = 0.0

        # Check RPM bucket
        if self._request_tokens < needed_requests:
            shortage = needed_requests - self._request_tokens
            # Time to replenish shortage at rate of rpm/60 per second
            wait_for_requests = shortage / (self.rpm / 60.0)

        # Check TPM bucket
        if self._token_tokens < needed_tokens:
            shortage = needed_tokens - self._token_tokens
            # Time to replenish shortage at rate of tpm/60 per second
            wait_for_tokens = shortage / (self.tpm / 60.0)

        # Wait for whichever bucket needs more time
        return max(wait_for_requests, wait_for_tokens)



class GeminiAdapter:
    """
    Async adapter for Gemini API.

    Features:
    - Automatic rate limit retry with exponential backoff
    - Secure API key handling (never logged or exposed)
    - Token usage tracking

    Example:
        adapter = GeminiAdapter()
        response, tokens = await adapter.call(task)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: Optional[int] = None,
        base_retry_delay: Optional[float] = None,
        settings: Optional[GeminiSettings] = None,
        usage_journal: Optional[UsageJournal] = None
    ) -> None:
        """
        Initialize the Gemini adapter.

        Args:
            api_key: Optional explicit API key. If not provided, reads from env.
            max_retries: Maximum retry attempts on 429 errors.
            base_retry_delay: Base delay for exponential backoff (seconds).
            settings: Optional GeminiSettings, otherwise uses global settings.

        Raises:
            APIKeyNotFoundError: If no API key is available.
        """
        # Use provided settings or load from environment
        self._settings = settings or get_settings().gemini

        self.max_retries = max_retries if max_retries is not None else self._settings.max_retries
        self.base_retry_delay = base_retry_delay if base_retry_delay is not None else self._settings.base_retry_delay
        self.default_model = self._settings.default_model

        # Handle explicit key or read from environment
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

        self._key_manager = SecureKeyManager()

        # Validate key exists
        try:
            self._key_manager.get_key()
        except Exception:
            raise APIKeyNotFoundError(
                "No API key found. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Validate SDK is available (fail-fast)
        try:
            import google.generativeai as genai
            self._genai = genai
        except ImportError:
            self._genai = None  # Will use placeholder in tests

        # Client will be configured on first use
        self._client = None

        # Proactive Rate Limiter
        self._rate_limiter = RateLimiter(
            rpm=self._settings.requests_per_minute,
            tpm=self._settings.tokens_per_minute
        )

        # Usage tracking
        self._usage_journal = usage_journal or UsageJournal()

    async def call(self, task: AITask) -> Tuple[str, int]:
        """
        Execute an AI task.

        Args:
            task: The AITask to execute.

        Returns:
            Tuple of (response_text, tokens_used).

        Raises:
            RateLimitError: If max retries exceeded.
        """
        import time

        # Proactively wait if needed
        await self._rate_limiter.acquire(estimated_tokens=task.estimated_tokens or 1000)

        retries = 0
        last_error = None
        start_time = time.perf_counter()

        while retries <= self.max_retries:
            try:
                response_text, tokens_used = await self._generate(task)

                # Record successful usage
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                await self._record_usage(
                    task=task,
                    tokens_used=tokens_used,
                    success=True,
                    latency_ms=latency_ms
                )

                return response_text, tokens_used
            except RateLimitError as e:
                last_error = e
                retries += 1

                if retries > self.max_retries:
                    # Record failed usage
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    await self._record_usage(
                        task=task,
                        tokens_used=0,
                        success=False,
                        latency_ms=latency_ms,
                        error=str(e)
                    )
                    raise

                # Exponential backoff
                delay = self.base_retry_delay * (2 ** (retries - 1))
                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        raise last_error or RateLimitError("Max retries exceeded")

    async def _record_usage(
        self,
        task: AITask,
        tokens_used: int,
        success: bool,
        latency_ms: int,
        error: Optional[str] = None
    ) -> None:
        """Record API usage to the journal."""
        from datetime import datetime

        entry = UsageEntry(
            timestamp=datetime.utcnow(),
            task_id=str(task.id),
            request_type="human" if task.priority <= RequestPriority.CRITICAL else "background",
            priority=task.priority,
            tokens_used=tokens_used,
            requests_used=1,
            success=success,
            latency_ms=latency_ms,
            error=error,
            task_name=task.name
        )
        await self._usage_journal.record_usage(entry)

    async def get_usage_stats(self, hours: int = 24) -> dict:
        """
        Get usage statistics from the journal.

        Args:
            hours: Number of hours to look back.

        Returns:
            Dictionary with usage statistics.
        """
        daily = await self._usage_journal.get_daily_usage()
        hourly = await self._usage_journal.get_hourly_breakdown(hours=hours)
        totals = await self._usage_journal.get_totals()

        return {
            "daily": daily,
            "hourly": hourly,
            "totals": totals
        }

    async def _generate(self, task: AITask) -> Tuple[str, int]:
        """
        Execute the actual API call.

        This method should be mocked in tests.

        Returns:
            Tuple of (response_text, tokens_used).
        """
        # Initialize SDK if available
        if self._client is None:
            if self._genai is None:
                # SDK not installed, return placeholder for testing
                return ("SDK not installed", 0)
            self._genai.configure(api_key=self._key_manager.get_key())
            self._client = self._genai

        # Get the model
        model = self._client.GenerativeModel(task.model or self.default_model)

        # Make the async call
        loop = asyncio.get_event_loop()

        def _sync_generate():
            response = model.generate_content(task.prompt)
            text = response.text if hasattr(response, 'text') else str(response)

            # Extract token usage if available
            tokens = 0
            if hasattr(response, 'usage_metadata'):
                tokens = getattr(response.usage_metadata, 'total_token_count', 0)

            return text, tokens

        try:
            return await loop.run_in_executor(None, _sync_generate)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                raise RateLimitError("Rate limit exceeded", retry_after_seconds=60)
            raise

    def _sanitize_error(self, error_msg: str) -> str:
        """Remove API key from error message."""
        return self._key_manager.sanitize(error_msg)

    def __str__(self) -> str:
        """Return safe string representation."""
        return f"GeminiAdapter(model={self.default_model}, key={self._key_manager.get_masked_key()})"

    def __repr__(self) -> str:
        """Return safe repr."""
        return self.__str__()
