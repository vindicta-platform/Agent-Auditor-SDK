"""
Unit tests for Agent-Auditor-SDK models.

Layer: Unit
Scope: Models and Schema validation.
"""

import pytest
from datetime import datetime
from uuid import UUID
from enum import IntEnum
from pydantic import ValidationError

from agent_auditor.models import (
    RequestPriority, 
    AITask, 
    TaskResult, 
    QuotaBudget, 
    TierLimits
)


# =============================================================================
# RequestPriority Tests
# =============================================================================

class TestRequestPriority:
    def test_priority_values_exist(self):
        # Arrange & Act & Assert
        assert hasattr(RequestPriority, 'HUMAN')
        assert hasattr(RequestPriority, 'CRITICAL')
        assert hasattr(RequestPriority, 'HIGH')
        assert hasattr(RequestPriority, 'NORMAL')
        assert hasattr(RequestPriority, 'LOW')
        assert hasattr(RequestPriority, 'BACKGROUND')

    def test_human_is_highest_priority(self):
        # Arrange & Act & Assert
        # Lower value = Higher priority
        assert RequestPriority.HUMAN < RequestPriority.CRITICAL
        assert RequestPriority.HUMAN < RequestPriority.BACKGROUND

    def test_priority_ordering(self):
        # Arrange
        priorities = [
            RequestPriority.BACKGROUND,
            RequestPriority.LOW,
            RequestPriority.NORMAL,
            RequestPriority.HIGH,
            RequestPriority.CRITICAL,
            RequestPriority.HUMAN,
        ]
        
        # Act
        sorted_priorities = sorted(priorities)
        
        # Assert
        assert sorted_priorities[0] == RequestPriority.HUMAN
        assert sorted_priorities[-1] == RequestPriority.BACKGROUND

    def test_priority_is_int_enum(self):
        # Arrange & Act & Assert
        assert issubclass(RequestPriority, IntEnum)


# =============================================================================
# AITask Tests
# =============================================================================

class TestAITask:
    def test_task_creation_with_required_fields(self):
        # Arrange & Act
        task = AITask(name="test_task", prompt="Test prompt")
        
        # Assert
        assert task.name == "test_task"
        assert task.prompt == "Test prompt"

    def test_task_has_auto_generated_id(self):
        # Arrange & Act
        task = AITask(name="test", prompt="test")
        
        # Assert
        assert isinstance(task.id, UUID)

    def test_task_has_default_priority(self):
        # Arrange & Act
        task = AITask(name="test", prompt="test")
        
        # Assert
        assert task.priority == RequestPriority.NORMAL

    def test_task_has_default_model(self):
        # Arrange & Act
        task = AITask(name="test", prompt="test")
        
        # Assert
        assert task.model == "gemini-1.5-flash"

    def test_task_has_estimated_tokens(self):
        # Arrange & Act
        task = AITask(name="test", prompt="test", estimated_tokens=500)
        
        # Assert
        assert task.estimated_tokens == 500

    def test_task_has_created_timestamp(self):
        # Arrange & Act
        task = AITask(name="test", prompt="test")
        
        # Assert
        assert isinstance(task.created_at, datetime)

    def test_task_allows_zero_or_none_estimated_tokens(self):
        # Arrange & Act - Zero is allowed (rate limiter uses fallback)
        task_zero = AITask(name="test", prompt="test", estimated_tokens=0)
        task_none = AITask(name="test2", prompt="test2")  # Default is None
        
        # Assert
        assert task_zero.estimated_tokens == 0
        assert task_none.estimated_tokens is None

    def test_task_accepts_priority_override(self):
        # Arrange & Act
        task = AITask(name="urgent", prompt="test", priority=RequestPriority.HUMAN)
        
        # Assert
        assert task.priority == RequestPriority.HUMAN


# =============================================================================
# TaskResult Tests
# =============================================================================

class TestTaskResult:
    def test_result_creation_with_required_fields(self):
        # Arrange
        from uuid import uuid4
        task_id = uuid4()
        
        # Act
        result = TaskResult(task_id=task_id, status="success")
        
        # Assert
        assert result.task_id == task_id
        assert result.status == "success"

    def test_result_status_is_constrained(self):
        # Arrange
        from uuid import uuid4
        
        # Act & Assert (Valid)
        for status in ["success", "failed", "queued", "cancelled"]:
            result = TaskResult(task_id=uuid4(), status=status)
            assert result.status == status
        
        # Act & Assert (Invalid)
        with pytest.raises(ValidationError):
            TaskResult(task_id=uuid4(), status="invalid")

    def test_result_has_optional_response(self):
        # Arrange
        from uuid import uuid4
        
        # Act
        result = TaskResult(
            task_id=uuid4(),
            status="success",
            response="Generated text response"
        )
        
        # Assert
        assert result.response == "Generated text response"

    def test_result_has_optional_error(self):
        # Arrange
        from uuid import uuid4
        
        # Act
        result = TaskResult(
            task_id=uuid4(),
            status="failed",
            error="API rate limit exceeded"
        )
        
        # Assert
        assert result.error == "API rate limit exceeded"

    def test_result_tracks_tokens_used(self):
        # Arrange
        from uuid import uuid4
        
        # Act
        result = TaskResult(
            task_id=uuid4(),
            status="success",
            tokens_used=150
        )
        
        # Assert
        assert result.tokens_used == 150

    def test_result_tracks_latency(self):
        # Arrange
        from uuid import uuid4
        
        # Act
        result = TaskResult(
            task_id=uuid4(),
            status="success",
            latency_ms=234
        )
        
        # Assert
        assert result.latency_ms == 234

    def test_result_has_completed_timestamp(self):
        # Arrange
        from uuid import uuid4
        
        # Act
        result = TaskResult(task_id=uuid4(), status="success")
        
        # Assert
        assert isinstance(result.completed_at, datetime)


# =============================================================================
# Additional Model Tests
# =============================================================================

class TestQuotaBudget:
    def test_budget_has_requests_available(self):
        # Arrange
        from datetime import datetime, timedelta
        
        # Act
        budget = QuotaBudget(
            requests_available=100,
            tokens_available=50000,
            window_end=datetime.utcnow() + timedelta(hours=1)
        )
        
        # Assert
        assert budget.requests_available == 100

    def test_budget_has_confidence(self):
        # Arrange
        from datetime import datetime, timedelta
        
        # Act
        budget = QuotaBudget(
            requests_available=100,
            tokens_available=50000,
            window_end=datetime.utcnow() + timedelta(hours=1),
            confidence=0.85
        )
        
        # Assert
        assert budget.confidence == 0.85

    def test_budget_has_human_reserve(self):
        # Arrange
        from datetime import datetime, timedelta
        
        # Act
        budget = QuotaBudget(
            requests_available=100,
            tokens_available=50000,
            window_end=datetime.utcnow() + timedelta(hours=1),
            human_reserve_percent=30
        )
        
        # Assert
        assert budget.human_reserve_percent == 30


class TestTierLimits:
    def test_free_tier_defaults(self):
        # Arrange & Act
        limits = TierLimits()
        
        # Assert
        assert limits.requests_per_minute == 15
        assert limits.tokens_per_minute == 1_000_000
        assert limits.requests_per_day == 1500
        assert limits.tier_name == "free"
