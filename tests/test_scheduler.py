"""
Unit tests for ArbiterScheduler.

These tests MUST FAIL until scheduler.py is implemented.

Tests:
- T110: ArbiterScheduler.submit() with HUMAN priority
- T111: Preemption (human pauses background)
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestSchedulerSubmit:
    """T110: Tests for ArbiterScheduler.submit() with HUMAN priority."""

    @pytest.mark.asyncio
    async def test_submit_human_succeeds(self):
        """Human priority tasks should be processed immediately."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(
            name="human_query",
            prompt="What is the meta?",
            priority=RequestPriority.HUMAN
        )
        
        # Mock the API call
        with patch.object(scheduler, '_execute_task', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "Mock response"
            
            result = await scheduler.submit(task)
        
        assert result.status == "success"
        assert result.response == "Mock response"

    @pytest.mark.asyncio
    async def test_submit_background_queues(self):
        """Background priority tasks should be queued, not executed immediately."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(
            name="batch_job",
            prompt="Background work",
            priority=RequestPriority.BACKGROUND
        )
        
        result = await scheduler.submit(task)
        
        # Background tasks are queued for later
        assert result.status == "queued"
        assert scheduler.queue.size == 1

    @pytest.mark.asyncio
    async def test_submit_returns_task_result(self):
        """submit() should return a TaskResult."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority, TaskResult
        
        scheduler = ArbiterScheduler()
        
        task = AITask(
            name="test",
            prompt="test",
            priority=RequestPriority.HUMAN
        )
        
        with patch.object(scheduler, '_execute_task', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "Response"
            
            result = await scheduler.submit(task)
        
        assert isinstance(result, TaskResult)
        assert result.task_id == task.id

    @pytest.mark.asyncio
    async def test_submit_tracks_tokens_used(self):
        """submit() should track tokens used in result."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(name="test", prompt="test", priority=RequestPriority.HUMAN)
        
        with patch.object(scheduler, '_execute_task', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Response", 150)  # Response + tokens
            
            result = await scheduler.submit(task)
        
        assert result.tokens_used > 0


class TestSchedulerPreemption:
    """T111: Tests for preemption (human pauses background)."""

    @pytest.mark.asyncio
    async def test_background_pauses_for_human(self):
        """Background processing should pause when human request arrives."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        # Start background processing
        scheduler._background_processing = True
        
        # Submit human task
        task = AITask(name="urgent", prompt="help", priority=RequestPriority.HUMAN)
        
        with patch.object(scheduler, '_execute_task', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "Done"
            
            # During human request, background should be paused
            result = await scheduler.submit(task)
        
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_get_status_returns_dashboard_data(self):
        """get_status() should return dashboard data."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        # Add some tasks
        for i in range(3):
            task = AITask(name=f"bg_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await scheduler.submit(task)
        
        status = scheduler.get_status()
        
        assert "queue_size" in status
        assert status["queue_size"] == 3
        assert "background_processing" in status

    @pytest.mark.asyncio
    async def test_human_never_blocked_by_background(self):
        """Human requests should never wait for background tasks."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        import asyncio
        import time
        
        scheduler = ArbiterScheduler()
        
        # Queue many background tasks
        for i in range(100):
            bg_task = AITask(name=f"bg_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await scheduler.submit(bg_task)
        
        # Human request should still be fast
        human_task = AITask(name="human", prompt="help", priority=RequestPriority.HUMAN)
        
        with patch.object(scheduler, '_execute_task', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "Fast response"
            
            start = time.perf_counter()
            result = await scheduler.submit(human_task)
            elapsed = time.perf_counter() - start
        
        # Should complete quickly (not waiting for 100 background tasks)
        assert result.status == "success"
        assert elapsed < 0.1  # Less than 100ms


class TestSchedulerRouting:
    """Tests for task routing logic."""

    @pytest.mark.asyncio
    async def test_route_human_to_immediate(self):
        """_route_task should route HUMAN to immediate execution."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(name="human", prompt="p", priority=RequestPriority.HUMAN)
        
        route = scheduler._route_task(task)
        
        assert route == "immediate"

    @pytest.mark.asyncio
    async def test_route_critical_to_immediate(self):
        """_route_task should route CRITICAL to immediate execution."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(name="critical", prompt="p", priority=RequestPriority.CRITICAL)
        
        route = scheduler._route_task(task)
        
        assert route == "immediate"

    @pytest.mark.asyncio
    async def test_route_background_to_queue(self):
        """_route_task should route BACKGROUND to queue."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(name="bg", prompt="p", priority=RequestPriority.BACKGROUND)
        
        route = scheduler._route_task(task)
        
        assert route == "queue"


class TestSchedulerQuotaIntegration:
    """Tests for quota tracking integration."""

    @pytest.mark.asyncio
    async def test_records_usage_after_execution(self):
        """Scheduler should record usage after task execution."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority
        
        scheduler = ArbiterScheduler()
        
        task = AITask(name="test", prompt="p", priority=RequestPriority.HUMAN)
        
        with patch.object(scheduler, '_execute_task', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "Response"
            
            await scheduler.submit(task)
        
        # Usage should be tracked
        assert scheduler._total_requests_today >= 1

    @pytest.mark.asyncio
    async def test_respects_daily_limit(self):
        """Scheduler should respect daily request limit."""
        from agent_auditor.scheduler import ArbiterScheduler
        from agent_auditor.models import AITask, RequestPriority, TierLimits
        from agent_auditor.errors import QuotaExhaustedError
        
        scheduler = ArbiterScheduler(tier_limits=TierLimits())
        
        # Simulate exhausted daily quota
        scheduler._total_requests_today = 1500  # Free tier limit
        
        task = AITask(name="blocked", prompt="p", priority=RequestPriority.HUMAN)
        
        with pytest.raises(QuotaExhaustedError):
            await scheduler.submit(task)
