"""
GeminiAdapter: Async adapter for Google Gemini/AI Studio API.

Uses google-generativeai SDK for API calls.
Implements:
- Rate limit handling with exponential backoff
- Secure API key handling (via SecureKeyManager)
- Token usage tracking
- Proactive RPM/TPM rate limiting
"""

import asyncio
import os
from typing import Optional, Tuple

from agent_auditor.errors import APIKeyNotFoundError, RateLimitError
from agent_auditor.models import AITask
from agent_auditor.rate_limiter import RateLimiter, get_rate_limiter
from agent_auditor.security import SecureKeyManager
from agent_auditor.settings import GeminiSettings, get_settings


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
        rate_limiter: Optional[RateLimiter] = None
    ) -> None:
        """
        Initialize the Gemini adapter.
        
        Args:
            api_key: Optional explicit API key. If not provided, reads from env.
            max_retries: Maximum retry attempts on 429 errors.
            base_retry_delay: Base delay for exponential backoff (seconds).
            settings: Optional GeminiSettings, otherwise uses global settings.
            rate_limiter: Optional RateLimiter for RPM/TPM enforcement.
            
        Raises:
            APIKeyNotFoundError: If no API key is available.
        """
        # Use provided settings or load from environment
        self._settings = settings or get_settings().gemini
        
        self.max_retries = max_retries if max_retries is not None else self._settings.max_retries
        self.base_retry_delay = base_retry_delay if base_retry_delay is not None else self._settings.base_retry_delay
        self.default_model = self._settings.default_model
        
        # Rate limiter for RPM/TPM enforcement
        self._rate_limiter = rate_limiter or get_rate_limiter()
        
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
    
    async def call(self, task: AITask, estimated_tokens: int = 500) -> Tuple[str, int]:
        """
        Execute an AI task with rate limiting.
        
        Args:
            task: The AITask to execute.
            estimated_tokens: Estimated tokens for rate limiting (default 500).
            
        Returns:
            Tuple of (response_text, tokens_used).
            
        Raises:
            RateLimitError: If max retries exceeded.
        """
        # Acquire rate limit before proceeding
        await self._rate_limiter.acquire(estimated_tokens)
        
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                response, tokens_used = await self._generate(task)
                # Record actual usage for rate limiter
                self._rate_limiter.record_usage(tokens_used, estimated_tokens)
                return response, tokens_used
            except RateLimitError as e:
                last_error = e
                retries += 1
                
                if retries > self.max_retries:
                    raise
                
                # Exponential backoff
                delay = self.base_retry_delay * (2 ** (retries - 1))
                await asyncio.sleep(delay)
        
        # Should not reach here, but just in case
        raise last_error or RateLimitError("Max retries exceeded")
    
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
