"""
Unit tests for RateLimiter (Token Bucket implementation).

Layer: Unit
Scope: Rate limiting logic.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from agent_auditor.adapters.gemini import RateLimiter


class TestTokenBucketAcquire:
    
    @pytest.mark.asyncio
    async def test_initial_tokens_available(self):
        # Arrange
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await limiter.acquire(estimated_tokens=100)
            
            # Assert
            assert result is True
            mock_sleep.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_proactive_waiting_when_tokens_exhausted(self):
        # Arrange
        limiter = RateLimiter(rpm=2, tpm=1000)
        # Exhaust RPM tokens
        await limiter.acquire(estimated_tokens=10)
        await limiter.acquire(estimated_tokens=10)
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await limiter.acquire(estimated_tokens=10)
            
            # Assert
            assert result is True
            mock_sleep.assert_called_once()
            wait_time = mock_sleep.call_args[0][0]
            assert 20 < wait_time <= 30
    
    @pytest.mark.asyncio
    async def test_dual_tracking_rpm_and_tpm(self):
        # Arrange
        limiter = RateLimiter(rpm=60, tpm=1000)
        # First request consumes 900 TPM
        await limiter.acquire(estimated_tokens=900)
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire(estimated_tokens=900)
            
            # Assert
            mock_sleep.assert_called_once()
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time > 0
    
    @pytest.mark.asyncio
    async def test_replenish_tokens_over_time(self):
        # Arrange
        limiter = RateLimiter(rpm=60, tpm=60_000)
        await limiter.acquire(estimated_tokens=1000)
        # Simulate 10 seconds passing
        limiter._last_replenish -= 10
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await limiter.acquire(estimated_tokens=100)
            
            # Assert
            assert result is True


class TestRateLimiterGeminiCompliance:
    
    @pytest.mark.asyncio
    async def test_gemini_free_tier_limits(self):
        # Arrange
        limiter = RateLimiter(rpm=60, tpm=60_000)
        # Exhaust RPM
        for _ in range(60):
            await limiter.acquire(estimated_tokens=100)
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire(estimated_tokens=100)
            
            # Assert
            mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_large_token_requests_block_on_tpm(self):
        # Arrange
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire(estimated_tokens=70_000)
            
            # Assert
            mock_sleep.assert_called()


class TestRateLimiterEdgeCases:
    
    @pytest.mark.asyncio
    async def test_zero_token_request(self):
        # Arrange
        limiter = RateLimiter(rpm=60, tpm=60_000)
        
        # Act
        result = await limiter.acquire(estimated_tokens=0)
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_limits(self):
        # Arrange
        limiter = RateLimiter(rpm=10, tpm=10_000)
        tasks = [limiter.acquire(estimated_tokens=100) for _ in range(20)]
        
        # Act
        with patch('asyncio.sleep', new_callable=AsyncMock):
            results = await asyncio.gather(*tasks)
            
            # Assert
            assert all(results)


@pytest.mark.asyncio
async def test_rate_limiter_60_second_rule_compliance():
    # Arrange
    import time
    start = time.time()
    limiter = RateLimiter(rpm=60, tpm=60_000)
    
    # Act
    with patch('asyncio.sleep', new_callable=AsyncMock):
        for _ in range(100):
            await limiter.acquire(estimated_tokens=500)
    
    # Assert
    elapsed = time.time() - start
    assert elapsed < 60, f"Tests took {elapsed}s (limit: 60s)"
