"""
Task queue with priority ordering for Agent-Auditor-SDK.

Implements a priority queue that ensures HUMAN priority tasks
are always processed first, with FIFO ordering within each priority level.

Supports optional persistence via SQLiteStorage for restart survival (NFR-002).
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from heapq import heappush, heappop
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from agent_auditor.models import AITask, RequestPriority

if TYPE_CHECKING:
    from agent_auditor.persistence.sqlite import SQLiteStorage


class DuplicateTaskError(Exception):
    """Raised when attempting to enqueue a task with duplicate ID."""
    pass


@dataclass(order=True)
class PrioritizedTask:
    """
    Wrapper for heap-based priority queue.
    
    Ordering: (priority, sequence_number) ensures stable priority ordering
    with FIFO within same priority level.
    """
    priority: int
    sequence: int
    task: AITask = field(compare=False)


class TaskQueue:
    """
    Priority queue for AI tasks.
    
    Features:
    - HUMAN priority (0) always dequeued first
    - FIFO ordering within same priority level
    - Optional SQLite persistence for restart survival
    - Duplicate ID detection
    
    Example:
        queue = TaskQueue()
        await queue.enqueue(task)
        next_task = await queue.dequeue()
    """
    
    def __init__(self, storage: Optional["SQLiteStorage"] = None) -> None:
        """
        Initialize the queue.
        
        Args:
            storage: Optional SQLiteStorage for persistence.
        """
        self._heap: list[PrioritizedTask] = []
        self._task_ids: set[UUID] = set()
        self._sequence = 0
        self._storage = storage
        self._lock = asyncio.Lock()
    
    @property
    def size(self) -> int:
        """Return number of tasks in queue."""
        return len(self._heap)
    
    async def enqueue(self, task: AITask) -> None:
        """
        Add a task to the queue.
        
        Args:
            task: The AITask to enqueue.
            
        Raises:
            DuplicateTaskError: If task ID already exists.
        """
        async with self._lock:
            if task.id in self._task_ids:
                raise DuplicateTaskError(f"Task with ID {task.id} already exists")
            
            # Persist if storage is configured
            if self._storage:
                await self._storage.save_task(task, status="pending")
            
            # Add to heap
            self._task_ids.add(task.id)
            prioritized = PrioritizedTask(
                priority=int(task.priority),
                sequence=self._sequence,
                task=task
            )
            heappush(self._heap, prioritized)
            self._sequence += 1
    
    async def dequeue(self) -> Optional[AITask]:
        """
        Remove and return the highest priority task.
        
        Returns:
            The highest priority task, or None if queue is empty.
        """
        async with self._lock:
            if not self._heap:
                return None
            
            prioritized = heappop(self._heap)
            self._task_ids.discard(prioritized.task.id)
            
            # Update status in storage if configured
            if self._storage:
                await self._storage.update_task_status(
                    prioritized.task.id, "processing"
                )
            
            return prioritized.task
    
    async def peek(self) -> Optional[AITask]:
        """
        Return the highest priority task without removing.
        
        Returns:
            The highest priority task, or None if queue is empty.
        """
        async with self._lock:
            if not self._heap:
                return None
            return self._heap[0].task
    
    async def load_from_storage(self) -> None:
        """Load pending tasks from storage (for restart recovery)."""
        if not self._storage:
            return
        
        pending = await self._storage.list_pending_tasks()
        for task in pending:
            if task.id not in self._task_ids:
                self._task_ids.add(task.id)
                prioritized = PrioritizedTask(
                    priority=int(task.priority),
                    sequence=self._sequence,
                    task=task
                )
                heappush(self._heap, prioritized)
                self._sequence += 1
    
    async def remove(self, task_id: UUID) -> Optional[AITask]:
        """
        Remove a specific task by ID.
        
        Returns:
            The removed task, or None if not found.
        """
        async with self._lock:
            # Find and remove task
            for i, prioritized in enumerate(self._heap):
                if prioritized.task.id == task_id:
                    self._heap.pop(i)
                    self._task_ids.discard(task_id)
                    # Re-heapify after removal
                    from heapq import heapify
                    heapify(self._heap)
                    
                    if self._storage:
                        await self._storage.update_task_status(task_id, "cancelled")
                    
                    return prioritized.task
            return None


@dataclass
class DeadLetterEntry:
    """Entry in the dead-letter queue."""
    task: AITask
    last_error: str
    attempts: int
    failed_at: datetime = field(default_factory=datetime.utcnow)


class DeadLetterQueue:
    """
    Queue for failed tasks that exceeded retry attempts.
    
    Tasks end up here after max retries, allowing for:
    - Manual inspection
    - Manual retry
    - Permanent removal
    """
    
    def __init__(self) -> None:
        """Initialize the dead-letter queue."""
        self._entries: dict[UUID, DeadLetterEntry] = {}
    
    @property
    def size(self) -> int:
        """Return number of entries in DLQ."""
        return len(self._entries)
    
    async def add(
        self, 
        task: AITask, 
        error: str, 
        attempts: int
    ) -> None:
        """
        Add a failed task to the DLQ.
        
        Args:
            task: The failed AITask.
            error: Last error message.
            attempts: Number of retry attempts made.
        """
        entry = DeadLetterEntry(
            task=task,
            last_error=error,
            attempts=attempts
        )
        self._entries[task.id] = entry
    
    async def get(self, task_id: UUID) -> Optional[DeadLetterEntry]:
        """Get a DLQ entry by task ID."""
        return self._entries.get(task_id)
    
    async def list_all(self) -> list[DeadLetterEntry]:
        """List all entries in the DLQ."""
        return list(self._entries.values())
    
    async def remove(self, task_id: UUID) -> Optional[AITask]:
        """
        Remove and return a task from the DLQ.
        
        Returns:
            The removed task, or None if not found.
        """
        entry = self._entries.pop(task_id, None)
        return entry.task if entry else None
    
    async def retry(self, task_id: UUID, queue: TaskQueue) -> bool:
        """
        Move a task from DLQ back to the main queue.
        
        Returns:
            True if successful, False if task not found.
        """
        entry = self._entries.pop(task_id, None)
        if entry:
            await queue.enqueue(entry.task)
            return True
        return False
