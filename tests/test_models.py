"""
Unit tests for Agent-Auditor-SDK models.

These tests MUST FAIL until models.py is implemented.

Tests:
- T010: RequestPriority enum
- T011: AITask model
- T012: TaskResult model
"""

import pytest
from datetime import datetime
from uuid import UUID


# =============================================================================
# T010: RequestPriority Enum Tests
# =============================================================================

class TestRequestPriority:
    """Tests for the RequestPriority enum."""

    def test_priority_values_exist(self):
        """RequestPriority should have HUMAN through BACKGROUND values."""
        from agent_auditor.models import RequestPriority
        
        assert hasattr(RequestPriority, 'HUMAN')
        assert hasattr(RequestPriority, 'CRITICAL')
        assert hasattr(RequestPriority, 'HIGH')
        assert hasattr(RequestPriority, 'NORMAL')
        assert hasattr(RequestPriority, 'LOW')
        assert hasattr(RequestPriority, 'BACKGROUND')

    def test_human_is_highest_priority(self):
        """HUMAN should have the lowest numeric value (highest priority)."""
        from agent_auditor.models import RequestPriority
        
        assert RequestPriority.HUMAN < RequestPriority.CRITICAL
        assert RequestPriority.HUMAN < RequestPriority.BACKGROUND

    def test_priority_ordering(self):
        """Priorities should be orderable from HUMAN (0) to BACKGROUND (5)."""
        from agent_auditor.models import RequestPriority
        
        priorities = [
            RequestPriority.BACKGROUND,
            RequestPriority.LOW,
            RequestPriority.NORMAL,
            RequestPriority.HIGH,
            RequestPriority.CRITICAL,
            RequestPriority.HUMAN,
        ]
        sorted_priorities = sorted(priorities)
        
        assert sorted_priorities[0] == RequestPriority.HUMAN
        assert sorted_priorities[-1] == RequestPriority.BACKGROUND

    def test_priority_is_int_enum(self):
        """RequestPriority should be an IntEnum for easy comparison."""
        from agent_auditor.models import RequestPriority
        from enum import IntEnum
        
        assert issubclass(RequestPriority, IntEnum)


# =============================================================================
# T011: AITask Model Tests
# =============================================================================

class TestAITask:
    """Tests for the AITask Pydantic model."""

    def test_task_creation_with_required_fields(self):
        """AITask should be creatable with name and prompt."""
        from agent_auditor.models import AITask
        
        task = AITask(name="test_task", prompt="Test prompt")
        
        assert task.name == "test_task"
        assert task.prompt == "Test prompt"

    def test_task_has_auto_generated_id(self):
        """AITask should auto-generate a UUID id."""
        from agent_auditor.models import AITask
        
        task = AITask(name="test", prompt="test")
        
        assert isinstance(task.id, UUID)

    def test_task_has_default_priority(self):
        """AITask should default to NORMAL priority."""
        from agent_auditor.models import AITask, RequestPriority
        
        task = AITask(name="test", prompt="test")
        
        assert task.priority == RequestPriority.NORMAL

    def test_task_has_default_model(self):
        """AITask should default to gemini-1.5-flash model."""
        from agent_auditor.models import AITask
        
        task = AITask(name="test", prompt="test")
        
        assert task.model == "gemini-1.5-flash"

    def test_task_has_estimated_tokens(self):
        """AITask should have an estimated_tokens field."""
        from agent_auditor.models import AITask
        
        task = AITask(name="test", prompt="test", estimated_tokens=500)
        
        assert task.estimated_tokens == 500

    def test_task_has_created_timestamp(self):
        """AITask should have a created_at timestamp."""
        from agent_auditor.models import AITask
        
        task = AITask(name="test", prompt="test")
        
        assert isinstance(task.created_at, datetime)

    def test_task_validates_positive_tokens(self):
        """AITask should reject non-positive estimated_tokens."""
        from agent_auditor.models import AITask
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            AITask(name="test", prompt="test", estimated_tokens=0)

    def test_task_accepts_priority_override(self):
        """AITask should accept a priority parameter."""
        from agent_auditor.models import AITask, RequestPriority
        
        task = AITask(name="urgent", prompt="test", priority=RequestPriority.HUMAN)
        
        assert task.priority == RequestPriority.HUMAN


# =============================================================================
# T012: TaskResult Model Tests
# =============================================================================

class TestTaskResult:
    """Tests for the TaskResult Pydantic model."""

    def test_result_creation_with_required_fields(self):
        """TaskResult should require task_id and status."""
        from agent_auditor.models import TaskResult
        from uuid import uuid4
        
        task_id = uuid4()
        result = TaskResult(task_id=task_id, status="success")
        
        assert result.task_id == task_id
        assert result.status == "success"

    def test_result_status_is_constrained(self):
        """TaskResult status should be one of: success, failed, queued, cancelled."""
        from agent_auditor.models import TaskResult
        from pydantic import ValidationError
        from uuid import uuid4
        
        # Valid statuses should work
        for status in ["success", "failed", "queued", "cancelled"]:
            result = TaskResult(task_id=uuid4(), status=status)
            assert result.status == status
        
        # Invalid status should fail
        with pytest.raises(ValidationError):
            TaskResult(task_id=uuid4(), status="invalid")

    def test_result_has_optional_response(self):
        """TaskResult should have an optional response field."""
        from agent_auditor.models import TaskResult
        from uuid import uuid4
        
        result = TaskResult(
            task_id=uuid4(),
            status="success",
            response="Generated text response"
        )
        
        assert result.response == "Generated text response"

    def test_result_has_optional_error(self):
        """TaskResult should have an optional error field."""
        from agent_auditor.models import TaskResult
        from uuid import uuid4
        
        result = TaskResult(
            task_id=uuid4(),
            status="failed",
            error="API rate limit exceeded"
        )
        
        assert result.error == "API rate limit exceeded"

    def test_result_tracks_tokens_used(self):
        """TaskResult should track tokens_used."""
        from agent_auditor.models import TaskResult
        from uuid import uuid4
        
        result = TaskResult(
            task_id=uuid4(),
            status="success",
            tokens_used=150
        )
        
        assert result.tokens_used == 150

    def test_result_tracks_latency(self):
        """TaskResult should track latency_ms."""
        from agent_auditor.models import TaskResult
        from uuid import uuid4
        
        result = TaskResult(
            task_id=uuid4(),
            status="success",
            latency_ms=234
        )
        
        assert result.latency_ms == 234

    def test_result_has_completed_timestamp(self):
        """TaskResult should have a completed_at timestamp."""
        from agent_auditor.models import TaskResult
        from uuid import uuid4
        
        result = TaskResult(task_id=uuid4(), status="success")
        
        assert isinstance(result.completed_at, datetime)


# =============================================================================
# Additional Model Tests
# =============================================================================

class TestQuotaBudget:
    """Tests for the QuotaBudget model."""

    def test_budget_has_requests_available(self):
        """QuotaBudget should have requests_available field."""
        from agent_auditor.models import QuotaBudget
        from datetime import datetime, timedelta
        
        budget = QuotaBudget(
            requests_available=100,
            tokens_available=50000,
            window_end=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert budget.requests_available == 100

    def test_budget_has_confidence(self):
        """QuotaBudget should have a confidence score."""
        from agent_auditor.models import QuotaBudget
        from datetime import datetime, timedelta
        
        budget = QuotaBudget(
            requests_available=100,
            tokens_available=50000,
            window_end=datetime.utcnow() + timedelta(hours=1),
            confidence=0.85
        )
        
        assert budget.confidence == 0.85

    def test_budget_has_human_reserve(self):
        """QuotaBudget should have human_reserve_percent."""
        from agent_auditor.models import QuotaBudget
        from datetime import datetime, timedelta
        
        budget = QuotaBudget(
            requests_available=100,
            tokens_available=50000,
            window_end=datetime.utcnow() + timedelta(hours=1),
            human_reserve_percent=30
        )
        
        assert budget.human_reserve_percent == 30


class TestTierLimits:
    """Tests for the TierLimits dataclass."""

    def test_free_tier_defaults(self):
        """TierLimits should default to Free Tier values."""
        from agent_auditor.models import TierLimits
        
        limits = TierLimits()
        
        assert limits.requests_per_minute == 15
        assert limits.tokens_per_minute == 1_000_000
        assert limits.requests_per_day == 1500
        assert limits.tier_name == "free"
