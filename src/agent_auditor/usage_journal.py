"""
SQLite-based usage journal for Agent-Auditor-SDK.

Provides async persistence for API call tracking and quota prediction.
"""

import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class UsageRecord:
    """Single API usage record."""
    timestamp: datetime
    endpoint: str
    tokens_used: int
    priority: int
    user_type: str  # 'HUMAN' or 'AGENT'
    success: bool


class UsageJournal:
    """
    Async SQLite journal for usage tracking.

    Features:
    - Persistent storage of API calls
    - Time-based queries for prediction
    - Automatic 30-day retention
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize usage journal.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.agent_auditor/journal.db
        """
        self.db_path = db_path or Path.home() / ".agent_auditor" / "journal.db"
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to database and ensure schema exists."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect
        self._conn = await aiosqlite.connect(str(self.db_path))

        # Create schema
        await self._create_schema()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_schema(self) -> None:
        """Create database schema."""
        if not self._conn:
            raise RuntimeError("Database not connected")

        # Usage journal table
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                endpoint TEXT NOT NULL,
                tokens_used INTEGER NOT NULL,
                priority INTEGER NOT NULL,
                user_type TEXT NOT NULL CHECK (user_type IN ('HUMAN', 'AGENT')),
                success BOOLEAN NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Quota snapshots table
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS quota_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                predicted_usage INTEGER NOT NULL,
                actual_usage INTEGER,
                confidence REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for time-based queries
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_timestamp
            ON usage_journal(timestamp)
        """)

        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_user_type
            ON usage_journal(user_type, timestamp)
        """)

        # Retention trigger (delete records older than 30 days)
        await self._conn.execute("""
            CREATE TRIGGER IF NOT EXISTS cleanup_old_records
            AFTER INSERT ON usage_journal
            BEGIN
                DELETE FROM usage_journal
                WHERE timestamp < datetime('now', '-30 days');
            END
        """)

        await self._conn.commit()

    async def record_usage(
        self,
        endpoint: str,
        tokens_used: int,
        priority: int,
        user_type: str,
        success: bool = True,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record an API usage event.

        Args:
            endpoint: API endpoint called
            tokens_used: Number of tokens consumed
            priority: Request priority (0-5)
            user_type: 'HUMAN' or 'AGENT'
            success: Whether the call succeeded
            timestamp: Optional timestamp (defaults to now)
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        ts = timestamp or datetime.utcnow()

        await self._conn.execute("""
            INSERT INTO usage_journal
            (timestamp, endpoint, tokens_used, priority, user_type, success)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ts, endpoint, tokens_used, priority, user_type, success))

        await self._conn.commit()

    async def get_usage_since(
        self,
        since: datetime,
        user_type: Optional[str] = None
    ) -> List[UsageRecord]:
        """
        Get usage records since a timestamp.

        Args:
            since: Start timestamp
            user_type: Optional filter by 'HUMAN' or 'AGENT'

        Returns:
            List of UsageRecord objects
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        if user_type:
            cursor = await self._conn.execute("""
                SELECT timestamp, endpoint, tokens_used, priority, user_type, success
                FROM usage_journal
                WHERE timestamp >= ? AND user_type = ?
                ORDER BY timestamp DESC
            """, (since, user_type))
        else:
            cursor = await self._conn.execute("""
                SELECT timestamp, endpoint, tokens_used, priority, user_type, success
                FROM usage_journal
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (since,))

        rows = await cursor.fetchall()
        return [
            UsageRecord(
                timestamp=datetime.fromisoformat(row[0]),
                endpoint=row[1],
                tokens_used=row[2],
                priority=row[3],
                user_type=row[4],
                success=bool(row[5])
            )
            for row in rows
        ]

    async def get_hourly_usage(
        self,
        hours: int = 24
    ) -> dict[int, int]:
        """
        Get usage grouped by hour.

        Args:
            hours: Number of hours to look back

        Returns:
            Dict mapping hour (0-23) to token count
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        since = datetime.utcnow() - timedelta(hours=hours)

        cursor = await self._conn.execute("""
            SELECT
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                SUM(tokens_used) as total_tokens
            FROM usage_journal
            WHERE timestamp >= ? AND success = 1
            GROUP BY hour
            ORDER BY hour
        """, (since,))

        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    async def save_prediction(
        self,
        predicted_usage: int,
        confidence: float,
        actual_usage: Optional[int] = None
    ) -> None:
        """
        Save a quota prediction snapshot.

        Args:
            predicted_usage: Predicted token usage
            confidence: Prediction confidence (0.0-1.0)
            actual_usage: Optional actual usage for validation
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        await self._conn.execute("""
            INSERT INTO quota_snapshots
            (timestamp, predicted_usage, actual_usage, confidence)
            VALUES (?, ?, ?, ?)
        """, (datetime.utcnow(), predicted_usage, actual_usage, confidence))

        await self._conn.commit()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.close()
