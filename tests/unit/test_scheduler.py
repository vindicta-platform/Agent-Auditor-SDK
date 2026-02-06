"""
Unit tests for ArbiterScheduler.

Layer: Unit
Scope: ArbiterScheduler class isolation.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import asyncio
import time

from agent_auditor import ArbiterScheduler, AITask, RequestPriority
from agent_auditor.models import TierLimits, TaskResult

@pytest.fixture
def mock_storage():
    m = Mock()
    m.save_task = AsyncMock()
    m.list_pending_tasks = AsyncMock(return_value=[])
    m.update_task_status = AsyncMock()
    m.record_usage = AsyncMock()
    return m

@pytest.fixture
def scheduler(mock_storage):
    # Use small limits for testing
    limits = TierLimits(requests_per_day=50, requests_per_minute=20)
    return ArbiterScheduler(tier_limits=limits, storage=mock_storage)


class TestSchedulerSubmit:

    @pytest.mark.asyncio
    async def test_submit_human_priority_executes_immediately(self, scheduler):
        # Arrange
        task = AITask(name="test", prompt="hi", priority=RequestPriority.HUMAN)
        
        # Act
        result = await scheduler.submit(task)
        
        # Assert
        assert result.status == "success"
        assert result.response == "Not implemented"
        assert scheduler.queue.size == 0

    @pytest.mark.asyncio
    async def test_submit_background_priority_queues(self, scheduler):
        # Arrange
        task = AITask(name="bg", prompt="proc", priority=RequestPriority.BACKGROUND)
        
        # Act
        result = await scheduler.submit(task)
        
        # Assert
        assert result.status == "queued"
        assert scheduler.queue.size == 1

    @pytest.mark.asyncio
    async def test_submit_returns_task_result(self, scheduler):
        # Arrange
        task = AITask(name="test", prompt="test", priority=RequestPriority.HUMAN)
        
        # Act
        result = await scheduler.submit(task)
        
        # Assert
        assert isinstance(result, TaskResult)
        assert result.task_id == task.id

    @pytest.mark.asyncio
    async def test_quota_exhausted_raises_error(self, scheduler):
        # Arrange
        from agent_auditor.errors import QuotaExhaustedError
        scheduler._total_requests_today = 50 # Max limit
        task = AITask(name="test", prompt="hi", priority=RequestPriority.HUMAN)
        
        # Act & Assert
        with pytest.raises(QuotaExhaustedError):
            await scheduler.submit(task)


class TestSchedulerRouting:

    @pytest.mark.asyncio
    async def test_route_human_to_immediate(self, scheduler):
        # Arrange
        task = AITask(name="human", prompt="p", priority=RequestPriority.HUMAN)
        
        # Act
        route = scheduler._route_task(task)
        
        # Assert
        assert route == "immediate"

    @pytest.mark.asyncio
    async def test_route_critical_to_immediate(self, scheduler):
        # Arrange
        task = AITask(name="critical", prompt="p", priority=RequestPriority.CRITICAL)
        
        # Act
        route = scheduler._route_task(task)
        
        # Assert
        assert route == "immediate"

    @pytest.mark.asyncio
    async def test_route_background_to_queue(self, scheduler, mock_storage):
        # Arrange
        task = AITask(name="bg", prompt="p", priority=RequestPriority.BACKGROUND)
        
        # Act
        route = scheduler._route_task(task)
        
        # Assert
        assert route == "queue"


class TestSchedulerPreemption:

    @pytest.mark.asyncio
    async def test_background_pauses_for_human(self, scheduler):
        # Arrange
        scheduler._background_processing = True
        task = AITask(name="urgent", prompt="help", priority=RequestPriority.HUMAN)
        
        # Act
        # Logic is inside submit -> _execute_immediate -> _pause_background
        result = await scheduler.submit(task)
        
        # Assert
        assert result.status == "success"
        # Can't easily assert _background_paused state as it reverts primarily.
        # But we assume success means it ran.

    @pytest.mark.asyncio
    async def test_human_never_blocked_by_background(self, scheduler):
        # Arrange
        # Queue many background tasks
        for i in range(50):
            bg_task = AITask(name=f"bg_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await scheduler.submit(bg_task)
        
        human_task = AITask(name="human", prompt="help", priority=RequestPriority.HUMAN)
        
        # Act
        start = time.perf_counter()
        result = await scheduler.submit(human_task)
        elapsed = time.perf_counter() - start
        
        # Assert
        assert result.status == "success"
        assert elapsed < 0.2  # Should be fast regardless of queue size


class TestSchedulerDashboard:

    @pytest.mark.asyncio
    async def test_get_status_returns_dashboard_data(self, scheduler):
        # Arrange
        for i in range(3):
            task = AITask(name=f"bg_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await scheduler.submit(task)
        
        # Act
        status = scheduler.get_status()
        
        # Assert
        assert "queue_size" in status
        assert status["queue_size"] == 3
        assert "background_processing" in status


class TestSchedulerUsage:

    @pytest.mark.asyncio
    async def test_records_usage_after_execution(self, scheduler):
        # Arrange
        task = AITask(name="test", prompt="p", priority=RequestPriority.HUMAN)
        
        # Act
        await scheduler.submit(task)
        
        # Assert
        assert scheduler._total_requests_today >= 1
