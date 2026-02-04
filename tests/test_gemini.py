"""
Unit tests for GeminiAdapter.

These tests MUST FAIL until adapters/gemini.py is implemented.

Tests:
- T120: GeminiAdapter.call() basic functionality
- T121: Rate limit handling (429)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import os


class TestGeminiAdapterInit:
    """Tests for GeminiAdapter initialization."""

    def test_requires_api_key(self):
        """GeminiAdapter should require an API key."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.errors import APIKeyNotFoundError
        
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("AISTUDIO__API_KEY", None)
        
        with pytest.raises(APIKeyNotFoundError):
            adapter = GeminiAdapter()

    def test_accepts_explicit_key(self):
        """GeminiAdapter should accept explicit API key."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        
        adapter = GeminiAdapter(api_key="test-key-123")
        
        assert adapter._key_manager is not None

    def test_reads_key_from_env(self):
        """GeminiAdapter should read key from environment."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        
        os.environ["GEMINI_API_KEY"] = "env-key-456"
        
        adapter = GeminiAdapter()
        
        # Should not raise
        assert adapter._key_manager is not None


class TestGeminiAdapterCall:
    """T120: Tests for GeminiAdapter.call()"""

    @pytest.mark.asyncio
    async def test_call_returns_response(self):
        """call() should return generated text."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        
        task = AITask(
            name="test",
            prompt="Say hello",
            model="gemini-1.5-flash"
        )
        
        # Mock the SDK call
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ("Hello!", 50)
            
            response, tokens = await adapter.call(task)
        
        assert response == "Hello!"
        assert tokens == 50

    @pytest.mark.asyncio
    async def test_call_uses_correct_model(self):
        """call() should use the model specified in task."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        
        task = AITask(
            name="test",
            prompt="Test",
            model="gemini-1.5-pro"
        )
        
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ("Response", 100)
            
            await adapter.call(task)
            
            # Should pass model to generate
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            assert task in call_args[0] or task == call_args[1].get('task')

    @pytest.mark.asyncio
    async def test_call_tracks_token_usage(self):
        """call() should return token usage from response."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        
        task = AITask(name="test", prompt="Count tokens")
        
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ("1 2 3 4 5", 150)
            
            response, tokens = await adapter.call(task)
        
        assert tokens == 150


class TestGeminiAdapterRateLimits:
    """T121: Tests for rate limit handling (429)."""

    @pytest.mark.asyncio
    async def test_handles_429_with_retry(self):
        """GeminiAdapter should retry on 429 with backoff."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        
        task = AITask(name="test", prompt="Test")
        
        # First call 429, second succeeds
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            from agent_auditor.errors import RateLimitError
            
            call_count = [0]
            
            async def mock_generate(task):
                call_count[0] += 1
                if call_count[0] == 1:
                    raise RateLimitError("429 Too Many Requests", retry_after_seconds=1)
                return ("Success after retry", 50)
            
            mock_gen.side_effect = mock_generate
            
            response, tokens = await adapter.call(task)
        
        assert response == "Success after retry"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_respects_max_retries(self):
        """GeminiAdapter should give up after max retries."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        from agent_auditor.errors import RateLimitError
        
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter(max_retries=3)
        
        task = AITask(name="test", prompt="Test")
        
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RateLimitError("429", retry_after_seconds=0)
            
            with pytest.raises(RateLimitError):
                await adapter.call(task)
        
        # Should have tried max_retries + 1 times
        assert mock_gen.call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """GeminiAdapter should use exponential backoff."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        from agent_auditor.errors import RateLimitError
        import asyncio
        
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter(max_retries=2, base_retry_delay=0.01)
        
        task = AITask(name="test", prompt="Test")
        
        delays = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(seconds):
            delays.append(seconds)
            # Don't actually sleep in tests
        
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RateLimitError("429", retry_after_seconds=0)
            
            with patch('asyncio.sleep', mock_sleep):
                with pytest.raises(RateLimitError):
                    await adapter.call(task)
        
        # Delays should increase exponentially
        if len(delays) >= 2:
            assert delays[1] > delays[0]


class TestGeminiAdapterSecurity:
    """Tests for API key security."""

    def test_key_not_in_str(self):
        """API key should not appear in str()."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        
        os.environ["GEMINI_API_KEY"] = "AIzaSyD_secret_key"
        adapter = GeminiAdapter()
        
        adapter_str = str(adapter)
        
        assert "AIzaSyD" not in adapter_str
        assert "secret" not in adapter_str

    def test_key_not_in_error_messages(self):
        """API key should not appear in error messages."""
        from agent_auditor.adapters.gemini import GeminiAdapter
        from agent_auditor.models import AITask
        
        os.environ["GEMINI_API_KEY"] = "secret_api_key_789"
        adapter = GeminiAdapter()
        
        task = AITask(name="test", prompt="Test")
        
        # Simulate an error with key in message
        error_msg = adapter._sanitize_error("Failed with key secret_api_key_789")
        
        assert "secret_api_key_789" not in error_msg
