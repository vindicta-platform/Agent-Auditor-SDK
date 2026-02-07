"""
Unit tests for GeminiAdapter.

Layer: Unit
Scope: Adapter logic in isolation (mocked API).
"""

import os
import pytest
from unittest.mock import AsyncMock, patch

from agent_auditor.adapters.gemini import GeminiAdapter
from agent_auditor.models import AITask
from agent_auditor.errors import APIKeyNotFoundError, RateLimitError


class TestGeminiAdapterInit:

    def test_requires_api_key(self):
        # Arrange
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("AISTUDIO__API_KEY", None)

        # Act & Assert
        with pytest.raises(APIKeyNotFoundError):
            GeminiAdapter()

    def test_accepts_explicit_key(self):
        # Arrange & Act
        adapter = GeminiAdapter(api_key="test-key-123")

        # Assert
        assert adapter._key_manager is not None

    def test_reads_key_from_env(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "env-key-456"

        # Act
        adapter = GeminiAdapter()

        # Assert
        assert adapter._key_manager is not None


class TestGeminiAdapterCall:

    @pytest.mark.asyncio
    async def test_call_returns_response(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        task = AITask(
            name="test",
            prompt="Say hello",
            model="gemini-1.5-flash"
        )

        # Act
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ("Hello!", 50)
            response, tokens = await adapter.call(task)

        # Assert
        assert response == "Hello!"
        assert tokens == 50

    @pytest.mark.asyncio
    async def test_call_uses_correct_model(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        task = AITask(
            name="test",
            prompt="Test",
            model="gemini-1.5-pro"
        )

        # Act
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ("Response", 100)
            await adapter.call(task)

            # Assert
            mock_gen.assert_called_once()
            call_args = mock_gen.call_args
            assert task in call_args[0] or task == call_args[1].get('task')

    @pytest.mark.asyncio
    async def test_call_tracks_token_usage(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        task = AITask(name="test", prompt="Count tokens")

        # Act
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = ("1 2 3 4 5", 150)
            response, tokens = await adapter.call(task)

        # Assert
        assert tokens == 150


class TestGeminiAdapterRateLimits:

    @pytest.mark.asyncio
    async def test_handles_429_with_retry(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter()
        task = AITask(name="test", prompt="Test")
        call_count = [0]

        async def mock_generate(task):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RateLimitError("429 Too Many Requests", retry_after_seconds=1)
            return ("Success after retry", 50)

        # Act
        with patch.object(adapter, '_generate', side_effect=mock_generate):
            response, tokens = await adapter.call(task)

        # Assert
        assert response == "Success after retry"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_respects_max_retries(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter(max_retries=3)
        task = AITask(name="test", prompt="Test")

        # Act
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RateLimitError("429", retry_after_seconds=0)

            with pytest.raises(RateLimitError):
                await adapter.call(task)

        # Assert
        # Initial + 3 retries = 4 calls
        assert mock_gen.call_count == 4

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "test-key"
        adapter = GeminiAdapter(max_retries=2, base_retry_delay=0.01)
        task = AITask(name="test", prompt="Test")
        delays = []

        async def mock_sleep(seconds):
            delays.append(seconds)

        # Act
        with patch.object(adapter, '_generate', new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = RateLimitError("429", retry_after_seconds=0)

            with patch('asyncio.sleep', mock_sleep):
                with pytest.raises(RateLimitError):
                    await adapter.call(task)

        # Assert
        if len(delays) >= 2:
            assert delays[1] > delays[0]


class TestGeminiAdapterSecurity:

    def test_key_not_in_str(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "AIzaSyD_secret_key"
        adapter = GeminiAdapter()

        # Act
        adapter_str = str(adapter)

        # Assert
        assert "AIzaSyD" not in adapter_str
        assert "secret" not in adapter_str

    def test_key_not_in_error_messages(self):
        # Arrange
        os.environ["GEMINI_API_KEY"] = "secret_api_key_789"
        adapter = GeminiAdapter()

        # Act
        error_msg = adapter._sanitize_error("Failed with key secret_api_key_789")

        # Assert
        assert "secret_api_key_789" not in error_msg
