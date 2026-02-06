"""
Rate Limiter for Gemini API.

Implements token bucket algorithm for RPM/TPM limits.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    rpm_limit: int = 60  # Requests per minute (free tier default)
    tpm_limit: int = 60_000  # Tokens per minute (Gemini Pro free tier)
    refill_interval: float = 60.0  # Seconds for bucket refill


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    refill_rate: float = field(init=False)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()
        # Tokens refill per second to reach capacity in 60s
        self.refill_rate = self.capacity / 60.0
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def consume(self, amount: int = 1) -> bool:
        """
        Attempt to consume tokens.
        
        Returns:
            True if tokens consumed, False if insufficient.
        """
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
    
    def wait_time(self, amount: int = 1) -> float:
        """
        Calculate wait time to have enough tokens.
        
        Returns:
            Seconds to wait, or 0 if tokens available.
        """
        self._refill()
        if self.tokens >= amount:
            return 0.0
        needed = amount - self.tokens
        return needed / self.refill_rate
    
    @property
    def available(self) -> float:
        """Return available tokens."""
        self._refill()
        return self.tokens


class RateLimiter:
    """
    Rate limiter for Gemini API with RPM and TPM enforcement.
    
    Ensures no 429 errors are passed to human users by:
    1. Tracking request rate (RPM)
    2. Tracking token rate (TPM)
    3. Proactively waiting when limits approach
    
    Example:
        limiter = RateLimiter()
        await limiter.acquire(estimated_tokens=500)
        # Make API call...
        limiter.record_usage(actual_tokens=478)
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        """Initialize rate limiter with config."""
        self.config = config or RateLimitConfig()
        
        # Token buckets for RPM and TPM
        self._rpm_bucket = TokenBucket(capacity=self.config.rpm_limit)
        self._tpm_bucket = TokenBucket(capacity=self.config.tpm_limit)
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def acquire(self, estimated_tokens: int = 100) -> None:
        """
        Acquire permission to make an API call.
        
        Waits if necessary to avoid hitting rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the request.
        """
        async with self._lock:
            # Check both limits
            rpm_wait = self._rpm_bucket.wait_time(1)
            tpm_wait = self._tpm_bucket.wait_time(estimated_tokens)
            
            wait_time = max(rpm_wait, tpm_wait)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Consume from both buckets
            self._rpm_bucket.consume(1)
            self._tpm_bucket.consume(estimated_tokens)
    
    def record_usage(self, actual_tokens: int, estimated_tokens: int = 100) -> None:
        """
        Record actual token usage after API call.
        
        Adjusts TPM bucket if actual differs from estimated.
        
        Args:
            actual_tokens: Actual tokens used.
            estimated_tokens: Previously estimated tokens.
        """
        # Adjust TPM bucket for difference
        diff = actual_tokens - estimated_tokens
        if diff > 0:
            # Used more than estimated, consume difference
            self._tpm_bucket.tokens = max(0, self._tpm_bucket.tokens - diff)
        elif diff < 0:
            # Used less than estimated, give back difference
            self._tpm_bucket.tokens = min(
                self._tpm_bucket.capacity,
                self._tpm_bucket.tokens - diff
            )
    
    def can_proceed(self, estimated_tokens: int = 100) -> bool:
        """
        Check if a call can proceed without waiting.
        
        Returns:
            True if both RPM and TPM limits allow.
        """
        return (
            self._rpm_bucket.wait_time(1) == 0 and
            self._tpm_bucket.wait_time(estimated_tokens) == 0
        )
    
    @property
    def rpm_available(self) -> float:
        """Return available RPM quota."""
        return self._rpm_bucket.available
    
    @property
    def tpm_available(self) -> float:
        """Return available TPM quota."""
        return self._tpm_bucket.available
    
    def get_status(self) -> dict:
        """Return current limiter status."""
        return {
            "rpm_available": round(self.rpm_available, 1),
            "rpm_limit": self.config.rpm_limit,
            "tpm_available": round(self.tpm_available),
            "tpm_limit": self.config.tpm_limit,
        }


# Global singleton for shared limiting
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get or create the global rate limiter."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter(config)
    return _global_limiter


def reset_rate_limiter() -> None:
    """Reset global rate limiter (for testing)."""
    global _global_limiter
    _global_limiter = None
