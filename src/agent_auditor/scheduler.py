"""
ArbiterScheduler: The core scheduler for Agent-Auditor-SDK.

Implements Constitution Principle I: Human Priority is Non-Negotiable.
Routes tasks based on priority, ensuring HUMAN requests are never blocked.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union, TYPE_CHECKING
from uuid import UUID

from agent_auditor.errors import QuotaExhaustedError
from agent_auditor.models import AITask, RequestPriority, TaskResult, TierLimits
from agent_auditor.queue import TaskQueue
from agent_auditor.settings import SchedulerSettings, get_settings

if TYPE_CHECKING:
    from agent_auditor.persistence.sqlite import SQLiteStorage


class ArbiterScheduler:
    """
    Priority-aware task scheduler.
    
    Core responsibilities:
    1. Route tasks based on priority (immediate vs queued)
    2. Execute HUMAN/CRITICAL tasks immediately
    3. Queue BACKGROUND tasks for surplus execution
    4. Respect quota limits
    
    Example:
        scheduler = ArbiterScheduler()
        result = await scheduler.submit(task)
    """
    
    def __init__(
        self, 
        tier_limits: Optional[TierLimits] = None,
        storage: Optional["SQLiteStorage"] = None,
        settings: Optional[SchedulerSettings] = None
    ) -> None:
        """
        Initialize the scheduler.
        
        Args:
            tier_limits: API limits (defaults to Free Tier).
            storage: Optional SQLite storage for persistence.
            settings: Optional SchedulerSettings, otherwise uses global settings.
        """
        # Use provided settings or load from environment
        self._settings = settings or get_settings().scheduler
        
        self.tier_limits = tier_limits or TierLimits()
        self.queue = TaskQueue(storage=storage)
        
        # Quota tracking
        self._total_requests_today = 0
        self._total_tokens_today = 0
        self._last_reset_date = datetime.utcnow().date()
        
        # Background processing state
        self._background_processing = False
        self._background_paused = False
        
        # Lock for quota updates
        self._quota_lock = asyncio.Lock()
    
    async def submit(self, task: AITask) -> TaskResult:
        """
        Submit a task for execution.
        
        HUMAN/CRITICAL tasks execute immediately.
        Other tasks are queued for batch processing.
        
        Args:
            task: The AITask to submit.
            
        Returns:
            TaskResult with status and response (if executed).
            
        Raises:
            QuotaExhaustedError: If daily quota is exhausted.
        """
        # Check daily quota
        await self._check_and_reset_quota()
        
        if self._total_requests_today >= self.tier_limits.requests_per_day:
            reset_time = datetime.combine(
                self._last_reset_date + timedelta(days=1),
                datetime.min.time()
            )
            raise QuotaExhaustedError(
                "Daily quota exhausted",
                reset_time=reset_time
            )
        
        # Route based on priority
        route = self._route_task(task)
        
        if route == "immediate":
            return await self._execute_immediate(task)
        else:
            return await self._queue_for_later(task)
    
    def _route_task(self, task: AITask) -> str:
        """
        Determine routing for a task.
        
        Args:
            task: The task to route.
            
        Returns:
            "immediate" for high priority, "queue" for background.
        """
        # Use settings threshold (default: HIGH priority and above are immediate)
        # Handle both IntEnum and int (Pydantic may coerce to int)
        priority_value = task.priority.value if hasattr(task.priority, 'value') else task.priority
        if priority_value <= self._settings.immediate_priority_threshold:
            return "immediate"
        return "queue"
    
    async def _execute_immediate(self, task: AITask) -> TaskResult:
        """Execute a task immediately."""
        start_time = time.perf_counter()
        
        try:
            # Pause background if running
            was_paused = self._background_paused
            self._background_paused = True
            
            try:
                response = await self._execute_task(task)
            finally:
                self._background_paused = was_paused
            
            # Parse response
            tokens_used = 0
            if isinstance(response, tuple):
                response_text, tokens_used = response
            else:
                response_text = response
            
            # Track usage
            async with self._quota_lock:
                self._total_requests_today += 1
                self._total_tokens_today += tokens_used
            
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            
            return TaskResult(
                task_id=task.id,
                status="success",
                response=response_text,
                tokens_used=tokens_used,
                latency_ms=elapsed_ms
            )
            
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            
            return TaskResult(
                task_id=task.id,
                status="failed",
                error=str(e),
                latency_ms=elapsed_ms
            )
    
    async def _queue_for_later(self, task: AITask) -> TaskResult:
        """Queue a task for later execution."""
        await self.queue.enqueue(task)
        
        return TaskResult(
            task_id=task.id,
            status="queued"
        )
    
    async def _execute_task(self, task: AITask) -> Union[str, Tuple[str, int]]:
        """
        Execute a task against the AI API.
        
        This is a stub that should be overridden or mocked in tests.
        The real implementation will use the GeminiAdapter.
        
        Returns:
            Either a response string, or (response, tokens_used) tuple.
        """
        # Placeholder - will be replaced by GeminiAdapter integration
        return "Not implemented"
    
    async def _check_and_reset_quota(self) -> None:
        """Reset quota counters if a new day has started."""
        today = datetime.utcnow().date()
        if today > self._last_reset_date:
            async with self._quota_lock:
                self._total_requests_today = 0
                self._total_tokens_today = 0
                self._last_reset_date = today
    
    def get_status(self) -> dict:
        """
        Get scheduler status for dashboard.
        
        Returns:
            Dictionary with queue size, processing state, quota usage.
        """
        return {
            "queue_size": self.queue.size,
            "background_processing": self._background_processing,
            "background_paused": self._background_paused,
            "requests_today": self._total_requests_today,
            "tokens_today": self._total_tokens_today,
            "requests_remaining": max(0, self.tier_limits.requests_per_day - self._total_requests_today),
            "tier": self.tier_limits.tier_name,
        }
    
    async def process_background_batch(self, max_tasks: int = 10) -> Tuple[int, int]:
        """
        Process a batch of background tasks.
        
        Args:
            max_tasks: Maximum tasks to process in this batch.
            
        Returns:
            Tuple of (processed_count, remaining_count).
        """
        self._background_processing = True
        processed = 0
        
        try:
            while processed < max_tasks and self.queue.size > 0:
                # Check if paused for human
                if self._background_paused:
                    break
                
                # Check quota
                if self._total_requests_today >= self.tier_limits.requests_per_day:
                    break
                
                task = await self.queue.dequeue()
                if task:
                    await self._execute_immediate(task)
                    processed += 1
                else:
                    break
        finally:
            self._background_processing = False
        
        return processed, self.queue.size
