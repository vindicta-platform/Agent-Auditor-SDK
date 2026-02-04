"""
Agent-Auditor-SDK: Quota-aware AI scheduling for the Vindicta Platform.

This SDK ensures human requests are NEVER blocked by background AI tasks
while maximizing utilization of available API quota.

Usage:
    from agent_auditor import ArbiterScheduler, RequestPriority

    scheduler = ArbiterScheduler()

    # Human requests always succeed (when quota exists)
    result = await scheduler.submit(task, priority=RequestPriority.HUMAN)

    # Background tasks queue until surplus quota is available
    result = await scheduler.submit(task, priority=RequestPriority.BACKGROUND)
"""

# Only import what is currently implemented
from agent_auditor.models import (
    RequestPriority,
    AITask,
    TaskResult,
    QuotaBudget,
    TierLimits,
    UsageEntry,
)

__version__ = "0.1.0"
__all__ = [
    "RequestPriority",
    "AITask",
    "TaskResult",
    "QuotaBudget",
    "TierLimits",
    "UsageEntry",
]

# These will be imported once implemented:
# from agent_auditor.scheduler import ArbiterScheduler
# from agent_auditor.queue import TaskQueue
# from agent_auditor.quota import QuotaPredictor
# from agent_auditor.security import SecureKeyManager
