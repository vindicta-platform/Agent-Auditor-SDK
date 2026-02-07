"""
TaskWorker: Background task execution with retry and dead-letter handling.

Processes tasks from the queue with:
- Exponential backoff on transient errors
- Dead-letter queue for permanent failures
- Quota-aware execution

Follows Constitution Principle I: Human Priority is Non-Negotiable.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from agent_auditor.errors import RateLimitError, TaskExecutionError
from agent_auditor.models import AITask, TaskResult

if TYPE_CHECKING:
    from agent_auditor.adapters.gemini import GeminiAdapter
    from agent_auditor.queue import TaskQueue, DeadLetterQueue
    from agent_auditor.quota import QuotaPredictor


class TaskWorker:
    """
    Background task worker with retry and dead-letter support.

    Example:
        worker = TaskWorker(queue=queue, dead_letter_queue=dlq)
        result = await worker.process_one()
    """

    def __init__(
        self,
        queue: "TaskQueue",
        dead_letter_queue: Optional["DeadLetterQueue"] = None,
        adapter: Optional["GeminiAdapter"] = None,
        quota_predictor: Optional["QuotaPredictor"] = None,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> None:
        """
        Initialize the task worker.

        Args:
            queue: TaskQueue to pull tasks from.
            dead_letter_queue: Optional DLQ for failed tasks.
            adapter: Optional GeminiAdapter for execution.
            quota_predictor: Optional QuotaPredictor for quota checks.
            max_retries: Maximum retry attempts.
            base_delay: Base delay for exponential backoff.
        """
        self.queue = queue
        self.dlq = dead_letter_queue
        self.adapter = adapter
        self.quota_predictor = quota_predictor
        self.max_retries = max_retries
        self.base_delay = base_delay

        # Track processed count
        self._processed_count = 0

    async def process_one(self) -> Optional[TaskResult]:
        """
        Process a single task from the queue.

        Returns:
            TaskResult if a task was processed, None if queue empty.
        """
        task = await self.queue.dequeue()
        if task is None:
            return None

        return await self._process_task(task)

    async def _process_task(self, task: AITask) -> TaskResult:
        """Process a task with retry logic."""
        retries = 0
        last_error: Optional[Exception] = None

        while retries <= self.max_retries:
            try:
                response, tokens = await self._execute(task)
                self._processed_count += 1

                return TaskResult(
                    task_id=task.id,
                    status="success",
                    response=response,
                    tokens_used=tokens
                )

            except TaskExecutionError as e:
                last_error = e

                # Non-retryable errors go straight to DLQ
                if not e.retryable:
                    break

                retries += 1
                if retries > self.max_retries:
                    break

                delay = self.base_delay * (2 ** (retries - 1))
                await asyncio.sleep(delay)

            except RateLimitError as e:
                last_error = e
                retries += 1

                if retries > self.max_retries:
                    break

                delay = max(e.retry_after_seconds, self.base_delay * (2 ** (retries - 1)))
                await asyncio.sleep(delay)

            except Exception as e:
                last_error = e
                break

        # Failed after all retries - send to DLQ
        if self.dlq:
            await self.dlq.add(task, str(last_error) if last_error else "Unknown error", retries)

        return TaskResult(
            task_id=task.id,
            status="failed",
            error=str(last_error) if last_error else "Max retries exceeded"
        )

    async def _execute(self, task: AITask) -> tuple[str, int]:
        """
        Execute a task.

        This method should be mocked in tests.

        Returns:
            Tuple of (response, tokens_used).
        """
        if self.adapter:
            return await self.adapter.call(task)

        # Placeholder for testing
        return ("Executed", 0)

    async def process_batch(self, max_tasks: int = 10) -> List[TaskResult]:
        """
        Process a batch of tasks.

        Args:
            max_tasks: Maximum tasks to process.

        Returns:
            List of TaskResults.
        """
        results = []

        for _ in range(max_tasks):
            result = await self.process_one()
            if result is None:
                break
            results.append(result)

        return results

    async def run_until_empty(self, max_tasks: int = 100) -> int:
        """
        Process tasks until queue is empty.

        Args:
            max_tasks: Maximum tasks to process.

        Returns:
            Number of tasks processed.
        """
        processed = 0

        while processed < max_tasks:
            result = await self.process_one()
            if result is None:
                break
            processed += 1

        return processed

    async def run_with_quota(self, max_tasks: int = 100) -> int:
        """
        Process tasks respecting quota limits.

        Args:
            max_tasks: Maximum tasks to process.

        Returns:
            Number of tasks processed.
        """
        processed = 0

        while processed < max_tasks:
            # Check quota if predictor available
            if self.quota_predictor:
                budget = await self.quota_predictor.get_safe_budget()
                if budget.requests_available <= 0:
                    break

            result = await self.process_one()
            if result is None:
                break

            if result.status == "success":
                processed += 1

            # Update quota tracking
            if self.quota_predictor and result.status == "success":
                # Record the usage
                from agent_auditor.models import UsageEntry, RequestPriority
                entry = UsageEntry(
                    timestamp=datetime.utcnow(),
                    task_id=str(result.task_id),
                    request_type="background",
                    priority=RequestPriority.BACKGROUND,
                    tokens_used=result.tokens_used or 0,
                    requests_used=1,
                    success=True,
                    latency_ms=result.latency_ms or 0
                )
                await self.quota_predictor.usage_journal.record_usage(entry)

        return processed
