"""
Unit tests for TaskQueue and DeadLetterQueue.

These tests MUST FAIL until queue.py is implemented.

Tests:
- T100-T102: TaskQueue operations
- T300-T301: DeadLetterQueue (Phase 5)
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4


class TestTaskQueueEnqueue:
    """T100: Tests for TaskQueue.enqueue()"""

    @pytest.mark.asyncio
    async def test_enqueue_adds_task(self):
        """enqueue() should add a task to the queue."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask
        
        queue = TaskQueue()
        task = AITask(name="test", prompt="prompt")
        
        await queue.enqueue(task)
        
        assert queue.size == 1

    @pytest.mark.asyncio
    async def test_enqueue_multiple_tasks(self):
        """enqueue() should handle multiple tasks."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask
        
        queue = TaskQueue()
        
        for i in range(5):
            task = AITask(name=f"task_{i}", prompt="prompt")
            await queue.enqueue(task)
        
        assert queue.size == 5

    @pytest.mark.asyncio
    async def test_enqueue_rejects_duplicate_id(self):
        """enqueue() should reject duplicate task IDs."""
        from agent_auditor.queue import TaskQueue, DuplicateTaskError
        from agent_auditor.models import AITask
        from uuid import uuid4
        
        queue = TaskQueue()
        task_id = uuid4()
        
        task1 = AITask(id=task_id, name="first", prompt="prompt")
        task2 = AITask(id=task_id, name="second", prompt="prompt")
        
        await queue.enqueue(task1)
        
        with pytest.raises(DuplicateTaskError):
            await queue.enqueue(task2)


class TestTaskQueueDequeue:
    """T101: Tests for TaskQueue.dequeue() with priority ordering."""

    @pytest.mark.asyncio
    async def test_dequeue_returns_highest_priority(self):
        """dequeue() should return highest priority task first."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        
        # Add tasks in non-priority order
        low = AITask(name="low", prompt="p", priority=RequestPriority.LOW)
        high = AITask(name="high", prompt="p", priority=RequestPriority.CRITICAL)
        normal = AITask(name="normal", prompt="p", priority=RequestPriority.NORMAL)
        
        await queue.enqueue(low)
        await queue.enqueue(high)
        await queue.enqueue(normal)
        
        # Dequeue should return highest priority first
        first = await queue.dequeue()
        assert first.name == "high"
        assert first.priority == RequestPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_human_priority_always_first(self):
        """HUMAN priority should always be dequeued first."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        
        # Add critical task first
        critical = AITask(name="critical", prompt="p", priority=RequestPriority.CRITICAL)
        await queue.enqueue(critical)
        
        # Then add human task
        human = AITask(name="human", prompt="p", priority=RequestPriority.HUMAN)
        await queue.enqueue(human)
        
        # Human should still come first
        first = await queue.dequeue()
        assert first.priority == RequestPriority.HUMAN

    @pytest.mark.asyncio
    async def test_dequeue_fifo_within_priority(self):
        """Within same priority, FIFO order should be preserved."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        import asyncio
        
        queue = TaskQueue()
        
        # Add multiple tasks with same priority
        for i in range(3):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.NORMAL)
            await queue.enqueue(task)
            await asyncio.sleep(0.001)  # Ensure ordering
        
        # Should come out in FIFO order
        t1 = await queue.dequeue()
        t2 = await queue.dequeue()
        t3 = await queue.dequeue()
        
        assert t1.name == "task_0"
        assert t2.name == "task_1"
        assert t3.name == "task_2"

    @pytest.mark.asyncio
    async def test_dequeue_empty_returns_none(self):
        """dequeue() on empty queue should return None."""
        from agent_auditor.queue import TaskQueue
        
        queue = TaskQueue()
        
        result = await queue.dequeue()
        
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_updates_size(self):
        """dequeue() should decrement size."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask
        
        queue = TaskQueue()
        task = AITask(name="test", prompt="p")
        
        await queue.enqueue(task)
        assert queue.size == 1
        
        await queue.dequeue()
        assert queue.size == 0


class TestTaskQueuePeek:
    """T102: Tests for TaskQueue.peek()"""

    @pytest.mark.asyncio
    async def test_peek_returns_highest_priority(self):
        """peek() should return highest priority without removing."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask, RequestPriority
        
        queue = TaskQueue()
        
        normal = AITask(name="normal", prompt="p", priority=RequestPriority.NORMAL)
        critical = AITask(name="critical", prompt="p", priority=RequestPriority.CRITICAL)
        
        await queue.enqueue(normal)
        await queue.enqueue(critical)
        
        # Peek should return critical
        peeked = await queue.peek()
        assert peeked.name == "critical"
        
        # Size should be unchanged
        assert queue.size == 2

    @pytest.mark.asyncio
    async def test_peek_empty_returns_none(self):
        """peek() on empty queue should return None."""
        from agent_auditor.queue import TaskQueue
        
        queue = TaskQueue()
        
        result = await queue.peek()
        
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_peeks_same_result(self):
        """Multiple peek() calls should return same task."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask
        
        queue = TaskQueue()
        task = AITask(name="stable", prompt="p")
        await queue.enqueue(task)
        
        peek1 = await queue.peek()
        peek2 = await queue.peek()
        peek3 = await queue.peek()
        
        assert peek1.id == peek2.id == peek3.id


class TestTaskQueuePersistence:
    """Tests for queue persistence (NFR-002)."""

    @pytest.mark.asyncio
    async def test_queue_persists_to_storage(self, temp_db_path):
        """Queue should persist to SQLite storage."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask
        from agent_auditor.persistence.sqlite import SQLiteStorage
        
        storage = SQLiteStorage(temp_db_path)
        await storage.initialize()
        
        queue = TaskQueue(storage=storage)
        task = AITask(name="persistent", prompt="test")
        
        await queue.enqueue(task)
        
        # Verify persisted
        loaded = await storage.load_task(task.id)
        assert loaded is not None
        assert loaded.name == "persistent"
        
        await storage.close()

    @pytest.mark.asyncio
    async def test_queue_survives_restart(self, temp_db_path):
        """Queue should survive simulated restart."""
        from agent_auditor.queue import TaskQueue
        from agent_auditor.models import AITask
        from agent_auditor.persistence.sqlite import SQLiteStorage
        
        # First session
        storage1 = SQLiteStorage(temp_db_path)
        await storage1.initialize()
        queue1 = TaskQueue(storage=storage1)
        
        task = AITask(name="survivor", prompt="test")
        await queue1.enqueue(task)
        await storage1.close()
        
        # Second session (simulated restart)
        storage2 = SQLiteStorage(temp_db_path)
        await storage2.initialize()
        queue2 = TaskQueue(storage=storage2)
        await queue2.load_from_storage()
        
        assert queue2.size == 1
        recovered = await queue2.peek()
        assert recovered.name == "survivor"
        
        await storage2.close()


class TestDeadLetterQueue:
    """T300-T301: Tests for DeadLetterQueue (Phase 5)."""

    @pytest.mark.asyncio
    async def test_dead_letter_stores_failed_task(self):
        """DeadLetterQueue should store failed tasks with error info."""
        from agent_auditor.queue import DeadLetterQueue
        from agent_auditor.models import AITask
        
        dlq = DeadLetterQueue()
        task = AITask(name="failed", prompt="p")
        error = "API Error: 500 Internal Server Error"
        
        await dlq.add(task, error=error, attempts=3)
        
        assert dlq.size == 1

    @pytest.mark.asyncio
    async def test_dead_letter_tracks_attempts(self):
        """DeadLetterQueue should track failure attempts."""
        from agent_auditor.queue import DeadLetterQueue
        from agent_auditor.models import AITask
        
        dlq = DeadLetterQueue()
        task = AITask(name="failed", prompt="p")
        
        await dlq.add(task, error="Error 1", attempts=3)
        
        entry = await dlq.get(task.id)
        
        assert entry.attempts == 3
        assert entry.last_error == "Error 1"

    @pytest.mark.asyncio
    async def test_dead_letter_list_all(self):
        """DeadLetterQueue should list all failed tasks."""
        from agent_auditor.queue import DeadLetterQueue
        from agent_auditor.models import AITask
        
        dlq = DeadLetterQueue()
        
        for i in range(3):
            task = AITask(name=f"failed_{i}", prompt="p")
            await dlq.add(task, error=f"Error {i}", attempts=i+1)
        
        all_failed = await dlq.list_all()
        
        assert len(all_failed) == 3

    @pytest.mark.asyncio
    async def test_dead_letter_retry_removes_from_dlq(self):
        """Retrying a task should remove it from DLQ."""
        from agent_auditor.queue import DeadLetterQueue
        from agent_auditor.models import AITask
        
        dlq = DeadLetterQueue()
        task = AITask(name="retry_me", prompt="p")
        
        await dlq.add(task, error="Error", attempts=1)
        assert dlq.size == 1
        
        removed = await dlq.remove(task.id)
        
        assert removed is not None
        assert dlq.size == 0
