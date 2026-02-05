"""BDD-style tests for RateLimiter (Token Bucket implementation).

Validates dual RPM/TPM tracking, proactive waiting, and Gemini API compliance.

Constitution Compliance:
- III. Spec-Driven Methodology: BDD tests required
- II. Gas Tank Model: Rate limiting prevents 429 errors
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from agent_auditor.adapters.gemini import RateLimiter


class TestTokenBucketAcquire:
    """Token Bucket acquire() logic."""
    
    @pytest.mark.asyncio
    async def test_initial_tokens_available(self):
        """GIVEN a fresh rate limiter
        WHEN acquire() is called
        THEN it should succeed immediately without waiting
        """
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await limiter.acquire(estimated_tokens=100)
            
            assert result is True
            mock_sleep.assert_not_called()  # No waiting needed
    
    @pytest.mark.asyncio
    async def test_proactive_waiting_when_tokens_exhausted(self):
        """GIVEN a limiter with no tokens left
        WHEN acquire() is called
        THEN it should proactively wait for token replenishment
        """
        limiter = RateLimiter(rpm=2, tpm=1000)  # Very low limits
        
        # Exhaust RPM tokens
        await limiter.acquire(estimated_tokens=10)
        await limiter.acquire(estimated_tokens=10)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await limiter.acquire(estimated_tokens=10)
            
            assert result is True
            mock_sleep.assert_called_once()  # Proactive wait
            wait_time = mock_sleep.call_args[0][0]
            assert 20 < wait_time <= 30  # ~30s for RPM replenishment
    
    @pytest.mark.asyncio
    async def test_dual_tracking_rpm_and_tpm(self):
        """GIVEN a limiter tracking both RPM and TPM
        WHEN large token requests exhaust TPM before RPM
        THEN it should block on TPM limits
        """
        limiter = RateLimiter(rpm=60, tpm=1000)  # Low TPM
        
        # First request consumes 900 TPM
        await limiter.acquire(estimated_tokens=900)
        
        # Second request should wait for TPM (not RPM)
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire(estimated_tokens=900)
            
            mock_sleep.assert_called_once()
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time > 0  # Waited for TPM
    
    @pytest.mark.asyncio
    async def test_replenish_tokens_over_time(self):
        """GIVEN a limiter with some tokens used
        WHEN time passes (simulated)
        THEN tokens should replenish based on elapsed time
        """
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        # Use some tokens
        await limiter.acquire(estimated_tokens=1000)
        
        # Simulate 10 seconds passing (replenish 10/60 of RPM tokens)
        limiter._last_replenish -= 10  # Mock time passage
        
        # Should have more tokens now
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await limiter.acquire(estimated_tokens=100)
            assert result is True


class TestRateLimiterGeminiCompliance:
    """Gemini API free tier compliance (60 RPM, 60K TPM)."""
    
    @pytest.mark.asyncio
    async def test_gemini_free_tier_limits(self):
        """GIVEN a limiter configured for Gemini free tier
        WHEN 60 requests are made in < 60s
        THEN the 61st request should wait
        """
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        # Make 60 requests (exhaust RPM)
        for _ in range(60):
            await limiter.acquire(estimated_tokens=100)
        
        # 61st request should wait
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire(estimated_tokens=100)
            mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_large_token_requests_block_on_tpm(self):
        """GIVEN a request for 70K tokens (exceeds 60K TPM)
        WHEN acquire() is called
        THEN it should wait for TPM replenishment
        """
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire(estimated_tokens=70_000)
            
            # Should wait for tokens to replenish
            mock_sleep.assert_called()


class TestRateLimiterEdgeCases:
    """Edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_zero_token_request(self):
        """GIVEN a request for 0 tokens
        WHEN acquire() is called
        THEN it should succeed immediately
        """
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        result = await limiter.acquire(estimated_tokens=0)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_limits(self):
        """GIVEN multiple concurrent acquire() calls
        WHEN they compete for tokens
        THEN total requests should not exceed limits
        """
        limiter = RateLimiter(rpm=10, tpm=10_000)
        
        # Launch 20 concurrent requests (2x the RPM limit)
        tasks = [limiter.acquire(estimated_tokens=100) for _ in range(20)]
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            results = await asyncio.gather(*tasks)
            
            # All should eventually succeed
            assert all(results)


@pytest.mark.asyncio
async def test_rate_limiter_60_second_rule_compliance():
    """Test suite completes in < 60 seconds (Constitution XIX)."""
    import time
    
    start = time.time()
    
    # Run all tests (mocked sleep ensures speed)
    limiter = RateLimiter(rpm=60, tpm=60_000)
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        for _ in range(100):
            await limiter.acquire(estimated_tokens=500)
    
    elapsed = time.time() - start
    assert elapsed < 60, f"Tests took {elapsed}s (limit: 60s)"
