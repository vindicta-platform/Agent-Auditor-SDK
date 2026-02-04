"""
Unit tests for TaskWorker.

These tests MUST FAIL until worker.py is implemented.

Tests:
- T310-T313: TaskWorker operations
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestTaskWorkerProcess:
    """T310: Tests for TaskWorker.process()"""

    @pytest.mark.asyncio
    async def test_process_executes_task(self):
        """process() should execute a task from the queue."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        
        task = AITask(name="test", prompt="Hello", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Response", 50)
            
            result = await worker.process_one()
        
        assert result is not None
        assert result.status == "success"
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_returns_none_on_empty_queue(self):
        """process_one() should return None when queue is empty."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        
        result = await worker.process_one()
        
        assert result is None

    @pytest.mark.asyncio
    async def test_process_updates_task_status(self):
        """process() should update task status after execution."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        
        task = AITask(name="test", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Done", 100)
            
            result = await worker.process_one()
        
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_process_batch_handles_multiple(self):
        """process_batch() should handle multiple tasks."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        
        # Add 5 tasks
        for i in range(5):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await queue.enqueue(task)
        
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Response", 50)
            
            results = await worker.process_batch(max_tasks=5)
        
        assert len(results) == 5
        assert mock_exec.call_count == 5


class TestTaskWorkerRetry:
    """T311: Tests for retry with backoff."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        """TaskWorker should retry on transient errors."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        from agent_auditor.errors import RateLimitError
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue, max_retries=3)
        
        task = AITask(name="retry_me", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        call_count = [0]
        
        async def mock_execute(task):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RateLimitError("429", retry_after_seconds=0)
            return ("Success after retry", 50)
        
        with patch.object(worker, '_execute', side_effect=mock_execute):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.process_one()
        
        assert result.status == "success"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_uses_exponential_backoff(self):
        """TaskWorker should use exponential backoff on retries."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        from agent_auditor.errors import RateLimitError
        import asyncio
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue, max_retries=3, base_delay=0.1)
        
        task = AITask(name="test", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        delays = []
        
        async def mock_execute(task):
            raise RateLimitError("429", retry_after_seconds=0)
        
        async def mock_sleep(seconds):
            delays.append(seconds)
        
        with patch.object(worker, '_execute', side_effect=mock_execute):
            with patch('asyncio.sleep', mock_sleep):
                result = await worker.process_one()
        
        # Should fail after max retries
        assert result.status == "failed"
        
        # Delays should increase
        if len(delays) >= 2:
            assert delays[1] >= delays[0]


class TestTaskWorkerDeadLetter:
    """T312: Tests for dead-letter on failure."""

    @pytest.mark.asyncio
    async def test_moves_to_dead_letter_after_max_retries(self):
        """TaskWorker should move task to DLQ after max retries."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue, DeadLetterQueue
        from agent_auditor.models import AITask, RequestPriority
        from agent_auditor.errors import TaskExecutionError
        
        queue = TaskQueue()
        dlq = DeadLetterQueue()
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq, max_retries=2)
        
        task = AITask(name="doomed", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        async def always_fail(task):
            raise TaskExecutionError("Permanent failure", retryable=False)
        
        with patch.object(worker, '_execute', side_effect=always_fail):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.process_one()
        
        assert result.status == "failed"
        assert dlq.size == 1

    @pytest.mark.asyncio
    async def test_dead_letter_preserves_error_info(self):
        """Dead-letter should include error information."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue, DeadLetterQueue
        from agent_auditor.models import AITask, RequestPriority
        from agent_auditor.errors import TaskExecutionError
        
        queue = TaskQueue()
        dlq = DeadLetterQueue()
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq, max_retries=1)
        
        task = AITask(name="error_task", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        async def fail_with_message(task):
            raise TaskExecutionError("Specific error message")
        
        with patch.object(worker, '_execute', side_effect=fail_with_message):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await worker.process_one()
        
        entry = await dlq.get(task.id)
        
        assert "Specific error message" in entry.last_error

    @pytest.mark.asyncio
    async def test_non_retryable_errors_go_to_dead_letter_immediately(self):
        """Non-retryable errors should skip retries and go to DLQ."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue, DeadLetterQueue
        from agent_auditor.models import AITask, RequestPriority
        from agent_auditor.errors import TaskExecutionError
        
        queue = TaskQueue()
        dlq = DeadLetterQueue()
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq, max_retries=5)
        
        task = AITask(name="bad_task", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        call_count = [0]
        
        async def non_retryable_error(task):
            call_count[0] += 1
            raise TaskExecutionError("Bad request", retryable=False)
        
        with patch.object(worker, '_execute', side_effect=non_retryable_error):
            await worker.process_one()
        
        # Should only try once (no retries)
        assert call_count[0] == 1
        assert dlq.size == 1


class TestTaskWorkerIntegration:
    """Integration-level tests for TaskWorker."""

    @pytest.mark.asyncio
    async def test_worker_runs_until_queue_empty(self):
        """run_until_empty() should process all tasks."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        
        # Add 10 tasks
        for i in range(10):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await queue.enqueue(task)
        
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Done", 50)
            
            processed = await worker.run_until_empty(max_tasks=20)
        
        assert processed == 10
        assert queue.size == 0

    @pytest.mark.asyncio
    async def test_worker_respects_quota(self):
        """Worker should stop when quota is exhausted."""
        from agent_auditor.worker import TaskWorker
        from agent_auditor.queue import TaskQueue
        from agent_auditor.quota import QuotaPredictor
        from agent_auditor.models import AITask, RequestPriority, TierLimits
        
        queue = TaskQueue()
        
        # Create predictor with very low limit
        limits = TierLimits(requests_per_day=5)
        predictor = QuotaPredictor(tier_limits=limits)
        
        worker = TaskWorker(queue=queue, quota_predictor=predictor)
        
        # Add 10 tasks
        for i in range(10):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await queue.enqueue(task)
        
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Done", 50)
            
            # Should stop at 5 (quota limit)
            processed = await worker.run_with_quota(max_tasks=20)
        
        # Should have processed up to limit
        assert processed <= 5
