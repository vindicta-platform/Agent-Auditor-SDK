"""
Unit tests for TaskQueue and DeadLetterQueue.

Layer: Unit
Scope: Queue operations and logic in isolation.
"""

import pytest
import asyncio
from uuid import uuid4
from agent_auditor.queue import TaskQueue, DuplicateTaskError, DeadLetterQueue
from agent_auditor.models import AITask, RequestPriority
from agent_auditor.persistence.sqlite import SQLiteStorage
from unittest.mock import Mock, AsyncMock

# =============================================================================
# TaskQueue Operations
# =============================================================================

class TestTaskQueueEnqueue:

    @pytest.mark.asyncio
    async def test_enqueue_adds_task(self):
        # Arrange
        queue = TaskQueue()
        task = AITask(name="test", prompt="prompt")
        
        # Act
        await queue.enqueue(task)
        
        # Assert
        assert queue.size == 1

    @pytest.mark.asyncio
    async def test_enqueue_multiple_tasks(self):
        # Arrange
        queue = TaskQueue()
        
        # Act
        for i in range(5):
            task = AITask(name=f"task_{i}", prompt="prompt")
            await queue.enqueue(task)
        
        # Assert
        assert queue.size == 5

    @pytest.mark.asyncio
    async def test_enqueue_rejects_duplicate_id(self):
        # Arrange
        queue = TaskQueue()
        task_id = uuid4()
        task1 = AITask(id=task_id, name="first", prompt="prompt")
        task2 = AITask(id=task_id, name="second", prompt="prompt")
        await queue.enqueue(task1)
        
        # Act & Assert
        with pytest.raises(DuplicateTaskError):
            await queue.enqueue(task2)


class TestTaskQueueDequeue:

    @pytest.mark.asyncio
    async def test_dequeue_returns_highest_priority(self):
        # Arrange
        queue = TaskQueue()
        low = AITask(name="low", prompt="p", priority=RequestPriority.LOW)
        high = AITask(name="high", prompt="p", priority=RequestPriority.CRITICAL)
        normal = AITask(name="normal", prompt="p", priority=RequestPriority.NORMAL)
        await queue.enqueue(low)
        await queue.enqueue(high)
        await queue.enqueue(normal)
        
        # Act
        first = await queue.dequeue()
        
        # Assert
        assert first.name == "high"
        assert first.priority == RequestPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_human_priority_always_first(self):
        # Arrange
        queue = TaskQueue()
        critical = AITask(name="critical", prompt="p", priority=RequestPriority.CRITICAL)
        await queue.enqueue(critical)
        human = AITask(name="human", prompt="p", priority=RequestPriority.HUMAN)
        await queue.enqueue(human)
        
        # Act
        first = await queue.dequeue()
        
        # Assert
        assert first.priority == RequestPriority.HUMAN

    @pytest.mark.asyncio
    async def test_dequeue_fifo_within_priority(self):
        # Arrange
        queue = TaskQueue()
        # Add multiple tasks with same priority
        for i in range(3):
            task = AITask(name=f"task_{i}", prompt="p", priority=RequestPriority.NORMAL)
            await queue.enqueue(task)
            await asyncio.sleep(0.001)  # Ensure ordering timestamp diff? (Implementation dependent)
        
        # Act
        t1 = await queue.dequeue()
        t2 = await queue.dequeue()
        t3 = await queue.dequeue()
        
        # Assert
        assert t1.name == "task_0"
        assert t2.name == "task_1"
        assert t3.name == "task_2"

    @pytest.mark.asyncio
    async def test_dequeue_empty_returns_none(self):
        # Arrange
        queue = TaskQueue()
        
        # Act
        result = await queue.dequeue()
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_updates_size(self):
        # Arrange
        queue = TaskQueue()
        task = AITask(name="test", prompt="p")
        await queue.enqueue(task)
        assert queue.size == 1
        
        # Act
        await queue.dequeue()
        
        # Assert
        assert queue.size == 0


class TestTaskQueuePeek:

    @pytest.mark.asyncio
    async def test_peek_returns_highest_priority(self):
        # Arrange
        queue = TaskQueue()
        normal = AITask(name="normal", prompt="p", priority=RequestPriority.NORMAL)
        critical = AITask(name="critical", prompt="p", priority=RequestPriority.CRITICAL)
        await queue.enqueue(normal)
        await queue.enqueue(critical)
        
        # Act
        peeked = await queue.peek()
        
        # Assert
        assert peeked.name == "critical"
        assert queue.size == 2

    @pytest.mark.asyncio
    async def test_peek_empty_returns_none(self):
        # Arrange
        queue = TaskQueue()
        
        # Act
        result = await queue.peek()
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_peeks_same_result(self):
        # Arrange
        queue = TaskQueue()
        task = AITask(name="stable", prompt="p")
        await queue.enqueue(task)
        
        # Act
        peek1 = await queue.peek()
        peek2 = await queue.peek()
        peek3 = await queue.peek()
        
        # Assert
        assert peek1.id == peek2.id == peek3.id


class TestTaskQueuePersistence:

    @pytest.mark.asyncio
    async def test_queue_persists_to_storage(self, temp_db_path):
        # Arrange
        storage = SQLiteStorage(temp_db_path)
        await storage.initialize()
        queue = TaskQueue(storage=storage)
        task = AITask(name="persistent", prompt="test")
        
        # Act
        await queue.enqueue(task)
        
        # Assert
        loaded = await storage.load_task(task.id)
        assert loaded is not None
        assert loaded.name == "persistent"
        
        await storage.close()

    @pytest.mark.asyncio
    async def test_queue_survives_restart(self, temp_db_path):
        # Arrange
        # Session 1
        storage1 = SQLiteStorage(temp_db_path)
        await storage1.initialize()
        queue1 = TaskQueue(storage=storage1)
        task = AITask(name="survivor", prompt="test")
        await queue1.enqueue(task)
        await storage1.close()
        
        # Session 2 (Restart)
        storage2 = SQLiteStorage(temp_db_path)
        await storage2.initialize()
        queue2 = TaskQueue(storage=storage2)
        
        # Act
        await queue2.load_from_storage()
        
        # Assert
        assert queue2.size == 1
        recovered = await queue2.peek()
        assert recovered.name == "survivor"
        
        await storage2.close()


class TestDeadLetterQueue:

    @pytest.mark.asyncio
    async def test_dead_letter_stores_failed_task(self):
        # Arrange
        dlq = DeadLetterQueue()
        task = AITask(name="failed", prompt="p")
        error = "API Error: 500 Internal Server Error"
        
        # Act
        await dlq.add(task, error=error, attempts=3)
        
        # Assert
        assert dlq.size == 1

    @pytest.mark.asyncio
    async def test_dead_letter_tracks_attempts(self):
        # Arrange
        dlq = DeadLetterQueue()
        task = AITask(name="failed", prompt="p")
        
        # Act
        await dlq.add(task, error="Error 1", attempts=3)
        entry = await dlq.get(task.id)
        
        # Assert
        assert entry.attempts == 3
        assert entry.last_error == "Error 1"

    @pytest.mark.asyncio
    async def test_dead_letter_list_all(self):
        # Arrange
        dlq = DeadLetterQueue()
        for i in range(3):
            task = AITask(name=f"failed_{i}", prompt="p")
            await dlq.add(task, error=f"Error {i}", attempts=i+1)
        
        # Act
        all_failed = await dlq.list_all()
        
        # Assert
        assert len(all_failed) == 3

    @pytest.mark.asyncio
    async def test_dead_letter_retry_removes_from_dlq(self):
        # Arrange
        dlq = DeadLetterQueue()
        task = AITask(name="retry_me", prompt="p")
        await dlq.add(task, error="Error", attempts=1)
        assert dlq.size == 1
        
        # Act
        removed = await dlq.remove(task.id)
        
        # Assert
        assert removed is not None
        assert dlq.size == 0
