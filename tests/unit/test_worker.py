"""
Unit tests for TaskWorker.

Layer: Unit
Scope: Worker processing logic in isolation.
"""

import pytest
from unittest.mock import AsyncMock, patch

from agent_auditor.worker import TaskWorker
from agent_auditor.queue import TaskQueue, DeadLetterQueue
from agent_auditor.models import AITask, RequestPriority, TierLimits
from agent_auditor.errors import RateLimitError, TaskExecutionError
from agent_auditor.quota import QuotaPredictor


class TestTaskWorkerProcess:

    @pytest.mark.asyncio
    async def test_process_executes_task(self):
        # Arrange
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        task = AITask(name="test", prompt="Hello", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        # Act
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Response", 50)
            result = await worker.process_one()
        
        # Assert
        assert result is not None
        assert result.status == "success"
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_returns_none_on_empty_queue(self):
        # Arrange
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        
        # Act
        result = await worker.process_one()
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_process_updates_task_status(self):
        # Arrange
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        task = AITask(name="test", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        # Act
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Done", 100)
            result = await worker.process_one()
        
        # Assert
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_process_batch_handles_multiple(self):
        # Arrange
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        for i in range(5):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await queue.enqueue(task)
        
        # Act
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Response", 50)
            results = await worker.process_batch(max_tasks=5)
        
        # Assert
        assert len(results) == 5
        assert mock_exec.call_count == 5


class TestTaskWorkerRetry:

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        # Arrange
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
        
        # Act
        with patch.object(worker, '_execute', side_effect=mock_execute):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.process_one()
        
        # Assert
        assert result.status == "success"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_uses_exponential_backoff(self):
        # Arrange
        queue = TaskQueue()
        worker = TaskWorker(queue=queue, max_retries=3, base_delay=0.1)
        task = AITask(name="test", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        delays = []
        
        async def mock_execute(task):
            raise RateLimitError("429", retry_after_seconds=0)
        
        async def mock_sleep(seconds):
            delays.append(seconds)
        
        # Act
        with patch.object(worker, '_execute', side_effect=mock_execute):
            with patch('asyncio.sleep', mock_sleep):
                result = await worker.process_one()
        
        # Assert
        assert result.status == "failed"
        if len(delays) >= 2:
            assert delays[1] >= delays[0]


class TestTaskWorkerDeadLetter:

    @pytest.mark.asyncio
    async def test_moves_to_dead_letter_after_max_retries(self):
        # Arrange
        queue = TaskQueue()
        dlq = DeadLetterQueue()
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq, max_retries=2)
        task = AITask(name="doomed", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        async def always_fail(task):
            raise TaskExecutionError("Permanent failure", retryable=False)
        
        # Act
        with patch.object(worker, '_execute', side_effect=always_fail):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await worker.process_one()
        
        # Assert
        assert result.status == "failed"
        assert dlq.size == 1

    @pytest.mark.asyncio
    async def test_dead_letter_preserves_error_info(self):
        # Arrange
        queue = TaskQueue()
        dlq = DeadLetterQueue()
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq, max_retries=1)
        task = AITask(name="error_task", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        
        async def fail_with_message(task):
            raise TaskExecutionError("Specific error message")
        
        # Act
        with patch.object(worker, '_execute', side_effect=fail_with_message):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await worker.process_one()
        
        # Assert
        entry = await dlq.get(task.id)
        assert "Specific error message" in entry.last_error

    @pytest.mark.asyncio
    async def test_non_retryable_errors_go_to_dead_letter_immediately(self):
        # Arrange
        queue = TaskQueue()
        dlq = DeadLetterQueue()
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq, max_retries=5)
        task = AITask(name="bad_task", prompt="p", priority=RequestPriority.BACKGROUND)
        await queue.enqueue(task)
        call_count = [0]
        
        async def non_retryable_error(task):
            call_count[0] += 1
            raise TaskExecutionError("Bad request", retryable=False)
        
        # Act
        with patch.object(worker, '_execute', side_effect=non_retryable_error):
            await worker.process_one()
        
        # Assert
        assert call_count[0] == 1
        assert dlq.size == 1


class TestTaskWorkerIntegration:

    @pytest.mark.asyncio
    async def test_worker_runs_until_queue_empty(self):
        # Arrange
        queue = TaskQueue()
        worker = TaskWorker(queue=queue)
        for i in range(10):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await queue.enqueue(task)
        
        # Act
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Done", 50)
            processed = await worker.run_until_empty(max_tasks=20)
        
        # Assert
        assert processed == 10
        assert queue.size == 0

    @pytest.mark.asyncio
    async def test_worker_respects_quota(self):
        # Arrange
        queue = TaskQueue()
        limits = TierLimits(requests_per_day=5)
        predictor = QuotaPredictor(tier_limits=limits)
        worker = TaskWorker(queue=queue, quota_predictor=predictor)
        for i in range(10):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.BACKGROUND)
            await queue.enqueue(task)
        
        # Act
        with patch.object(worker, '_execute', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Done", 50)
            processed = await worker.run_with_quota(max_tasks=20)
        
        # Assert
        # Should process up to quota limit (5)
        assert processed <= 5
