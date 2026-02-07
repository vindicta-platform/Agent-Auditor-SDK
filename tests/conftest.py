"""
Shared test fixtures for Agent-Auditor-SDK tests.

These fixtures provide common test infrastructure without implementing
any actual production code.
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure tests don't leak environment variables."""
    # Save original env
    original_env = os.environ.copy()
    yield
    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_api_key():
    """Set a mock API key for testing."""
    os.environ["GEMINI_API_KEY"] = "test-api-key-12345"
    return os.environ["GEMINI_API_KEY"]


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test_queue.db")


# =============================================================================
# Time Fixtures
# =============================================================================

@pytest.fixture
def frozen_time():
    """Return a fixed datetime for deterministic testing."""
    return datetime(2026, 2, 3, 22, 0, 0)


@pytest.fixture
def time_series():
    """Generate a week of hourly timestamps for prediction testing."""
    base = datetime(2026, 2, 3, 0, 0, 0)
    return [base - timedelta(hours=h) for h in range(24 * 7)]


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_gemini_response():
    """Create a mock successful Gemini API response."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Mock response from Gemini"}]
                },
                "finish_reason": "STOP"
            }
        ],
        "usage_metadata": {
            "prompt_token_count": 10,
            "candidates_token_count": 20,
            "total_token_count": 30
        }
    }


@pytest.fixture
def mock_gemini_rate_limited():
    """Create a mock 429 rate limit response."""
    from unittest.mock import MagicMock
    error = MagicMock()
    error.status_code = 429
    error.message = "Resource exhausted. Try again later."
    return error


# =============================================================================
# Quota Fixtures
# =============================================================================

@pytest.fixture
def free_tier_limits():
    """Return Free Tier API limits."""
    return {
        "rpm": 15,
        "tpm": 1_000_000,
        "rpd": 1500,
        "human_reserve_percent": 30
    }


# =============================================================================
# Task Fixtures (stubs - will be replaced after models are implemented)
# =============================================================================

@pytest.fixture
def sample_task_dict():
    """Return a sample task as a dictionary (before models exist)."""
    return {
        "id": str(uuid4()),
        "name": "test_task",
        "prompt": "Test prompt for Gemini",
        "model": "gemini-1.5-flash",
        "priority": 3,  # NORMAL
        "estimated_tokens": 100,
    }


@pytest.fixture
def sample_human_task_dict():
    """Return a sample human priority task."""
    return {
        "id": str(uuid4()),
        "name": "human_request",
        "prompt": "What is the best Space Marine list?",
        "model": "gemini-1.5-flash",
        "priority": 0,  # HUMAN
        "estimated_tokens": 50,
    }


@pytest.fixture
def sample_background_task_dict():
    """Return a sample background task."""
    return {
        "id": str(uuid4()),
        "name": "debate_simulation",
        "prompt": "Simulate a debate between T'au and Necrons",
        "model": "gemini-1.5-flash",
        "priority": 5,  # BACKGROUND
        "estimated_tokens": 500,
    }
