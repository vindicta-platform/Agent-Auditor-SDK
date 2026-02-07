"""
SQLite persistence layer for Agent-Auditor-SDK.

Provides async storage for:
- Task queue persistence (survives restarts)
- Usage history for prediction

Uses stdlib sqlite3 with async wrapper pattern.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID

from agent_auditor.models import AITask, RequestPriority, UsageEntry


class SQLiteStorage:
    """
    Async SQLite storage for tasks and usage data.

    Follows 12-Factor: all data is persisted externally.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initialize storage with database path.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    async def initialize(self) -> None:
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_sync)

    def _init_sync(self) -> None:
        """Synchronous initialization."""
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

        # Create tasks table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                model TEXT DEFAULT 'gemini-1.5-flash',
                priority INTEGER DEFAULT 3,
                estimated_tokens INTEGER DEFAULT 1000,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                metadata TEXT DEFAULT '{}'
            )
        """)

        # Create usage table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_id TEXT NOT NULL,
                task_name TEXT DEFAULT '',
                request_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                tokens_used INTEGER NOT NULL,
                requests_used INTEGER NOT NULL,
                success INTEGER NOT NULL,
                latency_ms INTEGER NOT NULL,
                error TEXT
            )
        """)

        # Create indexes
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage(timestamp)")

        self._conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._conn.close)
            self._conn = None

    async def list_tables(self) -> list[str]:
        """List all tables in the database."""
        loop = asyncio.get_event_loop()

        def _list() -> list[str]:
            assert self._conn is not None
            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return [row[0] for row in cursor.fetchall()]

        return await loop.run_in_executor(None, _list)

    async def save_task(self, task: AITask, status: str = "pending") -> None:
        """Save a task to the database."""
        loop = asyncio.get_event_loop()

        def _save() -> None:
            assert self._conn is not None
            self._conn.execute("""
                INSERT OR REPLACE INTO tasks
                (id, name, prompt, model, priority, estimated_tokens, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(task.id),
                task.name,
                task.prompt,
                task.model,
                int(task.priority),
                task.estimated_tokens,
                task.created_at.isoformat(),
                status
            ))
            self._conn.commit()

        await loop.run_in_executor(None, _save)

    async def load_task(self, task_id: UUID) -> Optional[AITask]:
        """Load a task by ID."""
        loop = asyncio.get_event_loop()

        def _load() -> Optional[AITask]:
            assert self._conn is not None
            cursor = self._conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (str(task_id),)
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return AITask(
                id=UUID(row["id"]),
                name=row["name"],
                prompt=row["prompt"],
                model=row["model"],
                priority=RequestPriority(row["priority"]),
                estimated_tokens=row["estimated_tokens"],
                created_at=datetime.fromisoformat(row["created_at"])
            )

        return await loop.run_in_executor(None, _load)

    async def list_pending_tasks(self) -> list[AITask]:
        """List pending tasks ordered by priority."""
        loop = asyncio.get_event_loop()

        def _list() -> list[AITask]:
            assert self._conn is not None
            cursor = self._conn.execute(
                "SELECT * FROM tasks WHERE status = 'pending' ORDER BY priority ASC, created_at ASC"
            )
            tasks = []
            for row in cursor.fetchall():
                tasks.append(AITask(
                    id=UUID(row["id"]),
                    name=row["name"],
                    prompt=row["prompt"],
                    model=row["model"],
                    priority=RequestPriority(row["priority"]),
                    estimated_tokens=row["estimated_tokens"],
                    created_at=datetime.fromisoformat(row["created_at"])
                ))
            return tasks

        return await loop.run_in_executor(None, _list)

    async def update_task_status(self, task_id: UUID, status: str) -> None:
        """Update a task's status."""
        loop = asyncio.get_event_loop()

        def _update() -> None:
            assert self._conn is not None
            self._conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status, str(task_id))
            )
            self._conn.commit()

        await loop.run_in_executor(None, _update)

    async def get_task_status(self, task_id: UUID) -> Optional[str]:
        """Get a task's status."""
        loop = asyncio.get_event_loop()

        def _get() -> Optional[str]:
            assert self._conn is not None
            cursor = self._conn.execute(
                "SELECT status FROM tasks WHERE id = ?",
                (str(task_id),)
            )
            row = cursor.fetchone()
            return row["status"] if row else None

        return await loop.run_in_executor(None, _get)

    async def record_usage(self, entry: UsageEntry) -> None:
        """Record a usage entry."""
        loop = asyncio.get_event_loop()

        def _record() -> None:
            assert self._conn is not None
            self._conn.execute("""
                INSERT INTO usage
                (timestamp, task_id, task_name, request_type, priority,
                 tokens_used, requests_used, success, latency_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.timestamp.isoformat(),
                entry.task_id,
                entry.task_name,
                entry.request_type,
                int(entry.priority),
                entry.tokens_used,
                entry.requests_used,
                1 if entry.success else 0,
                entry.latency_ms,
                entry.error
            ))
            self._conn.commit()

        await loop.run_in_executor(None, _record)

    async def get_usage_history(self, hours: int = 24) -> list[UsageEntry]:
        """Get usage history for the last N hours."""
        loop = asyncio.get_event_loop()
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        def _get() -> list[UsageEntry]:
            assert self._conn is not None
            cursor = self._conn.execute(
                "SELECT * FROM usage WHERE timestamp >= ? ORDER BY timestamp DESC",
                (cutoff,)
            )
            entries = []
            for row in cursor.fetchall():
                entries.append(UsageEntry(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    task_id=row["task_id"],
                    task_name=row["task_name"],
                    request_type=row["request_type"],
                    priority=RequestPriority(row["priority"]),
                    tokens_used=row["tokens_used"],
                    requests_used=row["requests_used"],
                    success=bool(row["success"]),
                    latency_ms=row["latency_ms"],
                    error=row["error"]
                ))
            return entries

        return await loop.run_in_executor(None, _get)

    async def get_usage_by_hour(self, hours: int = 1) -> dict:
        """Get aggregated usage stats for the last N hours."""
        loop = asyncio.get_event_loop()
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        def _get() -> dict:
            assert self._conn is not None
            cursor = self._conn.execute("""
                SELECT
                    SUM(tokens_used) as total_tokens,
                    SUM(requests_used) as total_requests,
                    COUNT(*) as entry_count
                FROM usage WHERE timestamp >= ?
            """, (cutoff,))
            row = cursor.fetchone()
            return {
                "total_tokens": row["total_tokens"] or 0,
                "total_requests": row["total_requests"] or 0,
                "entry_count": row["entry_count"] or 0
            }

        return await loop.run_in_executor(None, _get)
