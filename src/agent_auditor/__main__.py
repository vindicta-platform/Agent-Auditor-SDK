"""
Agent-Auditor-SDK CLI.

Usage:
    python -m agent_auditor status [--json]
    python -m agent_auditor submit "prompt" [--priority P] [--name NAME]
    python -m agent_auditor process [--max N]
"""

import argparse
import asyncio
import json
import sys
from typing import Optional

from agent_auditor.scheduler import ArbiterScheduler
from agent_auditor.models import AITask, RequestPriority
from agent_auditor.worker import TaskWorker
from agent_auditor.queue import TaskQueue, DeadLetterQueue


# Version
__version__ = "0.1.0"

# Global scheduler instance (lazy loaded)
_scheduler: Optional[ArbiterScheduler] = None


def get_scheduler() -> ArbiterScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ArbiterScheduler()
    return _scheduler


def get_version() -> str:
    """Get the CLI version."""
    return __version__


def status_command(json_format: bool = False) -> None:
    """Show scheduler status."""
    scheduler = get_scheduler()
    status = scheduler.get_status()

    if json_format:
        print(json.dumps(status, indent=2))
    else:
        print("Agent-Auditor-SDK Status")
        print("=" * 40)
        print(f"Queue Size: {status['queue_size']}")
        print(f"Requests Today: {status['requests_today']}")
        print(f"Remaining: {status['requests_remaining']}")
        print(f"Tier: {status['tier']}")
        print(f"Background Processing: {status['background_processing']}")


async def submit_command(
    prompt: str,
    priority: str = "normal",
    name: Optional[str] = None
) -> dict:
    """Submit a task to the scheduler."""
    scheduler = get_scheduler()

    # Parse priority
    priority_map = {
        "human": RequestPriority.HUMAN,
        "critical": RequestPriority.CRITICAL,
        "high": RequestPriority.HIGH,
        "normal": RequestPriority.NORMAL,
        "low": RequestPriority.LOW,
        "background": RequestPriority.BACKGROUND,
    }

    priority_enum = priority_map.get(priority.lower(), RequestPriority.NORMAL)

    task = AITask(
        name=name or "cli_task",
        prompt=prompt,
        priority=priority_enum
    )

    result = await scheduler.submit(task)

    return {
        "task_id": str(result.task_id),
        "status": result.status,
        "response": result.response,
    }


async def process_command(max_tasks: int = 10) -> dict:
    """Process background tasks."""
    scheduler = get_scheduler()

    worker = TaskWorker(
        queue=scheduler.queue,
        dead_letter_queue=DeadLetterQueue()
    )

    processed = await worker.run_until_empty(max_tasks=max_tasks)

    return {
        "processed": processed,
        "remaining": scheduler.queue.size,
    }


def get_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="agent-auditor",
        description="Agent-Auditor-SDK: Quota-aware AI scheduling"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status command
    status_parser = subparsers.add_parser("status", help="Show scheduler status")
    status_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )

    # submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a task")
    submit_parser.add_argument("prompt", help="The prompt to submit")
    submit_parser.add_argument(
        "--priority", "-p",
        default="normal",
        choices=["human", "critical", "high", "normal", "low", "background"],
        help="Task priority"
    )
    submit_parser.add_argument(
        "--name", "-n",
        help="Task name"
    )

    # process command
    process_parser = subparsers.add_parser("process", help="Process background tasks")
    process_parser.add_argument(
        "--max", "-m",
        type=int,
        default=10,
        help="Maximum tasks to process"
    )

    return parser


def cli(args: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = get_parser()
    parsed = parser.parse_args(args)

    if parsed.command is None:
        parser.print_help()
        return 0

    if parsed.command == "status":
        status_command(json_format=parsed.json)
        return 0

    elif parsed.command == "submit":
        result = asyncio.run(submit_command(
            prompt=parsed.prompt,
            priority=parsed.priority,
            name=parsed.name
        ))
        print(json.dumps(result, indent=2))
        return 0

    elif parsed.command == "process":
        result = asyncio.run(process_command(max_tasks=parsed.max))
        print(json.dumps(result, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(cli())
