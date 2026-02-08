import sqlite3
from datetime import datetime

from .models import UsageEntry


class UsageJournal:
    """
    Persistent log of all API interactions.
    """

    def __init__(self, db_path: str = "usage_journal.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    timestamp TEXT,
                    task_id TEXT,
                    request_type TEXT,
                    priority INTEGER,
                    tokens_used INTEGER,
                    requests_used INTEGER,
                    success BOOLEAN,
                    latency_ms INTEGER,
                    error TEXT,
                    task_name TEXT,
                    conversation_id TEXT
                )
            """)

    def log_usage(self, entry: UsageEntry):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO usage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.timestamp.isoformat(),
                    entry.task_id,
                    entry.request_type,
                    int(entry.priority),
                    entry.tokens_used,
                    entry.requests_used,
                    entry.success,
                    entry.latency_ms,
                    entry.error,
                    entry.task_name,
                    entry.conversation_id,
                ),
            )

    def query_by_conversation(self, conversation_id: str) -> list[UsageEntry]:
        """
        Retrieves all journal entries for a specific conversation.
        """
        entries = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM usage WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conversation_id,),
            )
            for row in cursor:
                entries.append(
                    UsageEntry(
                        timestamp=datetime.fromisoformat(row[0]),
                        task_id=row[1],
                        request_type=row[2],
                        priority=row[3],
                        tokens_used=row[4],
                        requests_used=row[5],
                        success=bool(row[6]),
                        latency_ms=row[7],
                        error=row[8],
                        task_name=row[9],
                        conversation_id=row[10],
                    )
                )
        return entries
