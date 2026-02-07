"""
Component tests for SQLite persistence layer.

Layer: Component
Scope: SQLiteStorage class with real file I/O (using temp files).
"""

import os
import tempfile
import pytest
from datetime import datetime
from uuid import uuid4

from agent_auditor.persistence.sqlite import SQLiteStorage
from agent_auditor.models import AITask, RequestPriority, UsageEntry


class TestSQLiteStorage:

    @pytest.fixture
    def db_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield os.path.join(tmpdir, "test.db")

    @pytest.mark.asyncio
    async def test_creates_database_on_init(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)

        # Act
        await storage.initialize()

        # Assert
        assert os.path.exists(db_path)
        await storage.close()

    @pytest.mark.asyncio
    async def test_creates_required_tables(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)
        await storage.initialize()

        # Act
        tables = await storage.list_tables()

        # Assert
        assert "tasks" in tables
        assert "usage" in tables
        await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_load_task(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)
        await storage.initialize()
        task = AITask(
            name="test_task",
            prompt="Test prompt",
            priority=RequestPriority.NORMAL
        )

        # Act
        await storage.save_task(task)
        loaded = await storage.load_task(task.id)

        # Assert
        assert loaded is not None
        assert loaded.name == "test_task"
        assert loaded.prompt == "Test prompt"
        await storage.close()

    @pytest.mark.asyncio
    async def test_load_returns_none_for_missing(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)
        await storage.initialize()

        # Act
        loaded = await storage.load_task(uuid4())

        # Assert
        assert loaded is None
        await storage.close()

    @pytest.mark.asyncio
    async def test_list_pending_tasks(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)
        await storage.initialize()
        t1 = AITask(name="low", prompt="p", priority=RequestPriority.LOW)
        t2 = AITask(name="high", prompt="p", priority=RequestPriority.CRITICAL)
        t3 = AITask(name="normal", prompt="p", priority=RequestPriority.NORMAL)

        # Act
        await storage.save_task(t1, status="pending")
        await storage.save_task(t2, status="pending")
        await storage.save_task(t3, status="pending")
        pending = await storage.list_pending_tasks()

        # Assert
        # Should be ordered by priority (highest first)
        assert len(pending) == 3
        assert pending[0].name == "high"
        assert pending[1].name == "normal"
        assert pending[2].name == "low"
        await storage.close()

    @pytest.mark.asyncio
    async def test_update_task_status(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)
        await storage.initialize()
        task = AITask(name="test", prompt="p")
        await storage.save_task(task, status="pending")

        # Act
        await storage.update_task_status(task.id, "completed")
        status = await storage.get_task_status(task.id)

        # Assert
        assert status == "completed"
        await storage.close()

    @pytest.mark.asyncio
    async def test_record_usage(self, db_path):
        # Arrange
        storage = SQLiteStorage(db_path)
        await storage.initialize()
        entry = UsageEntry(
            timestamp=datetime.utcnow(),
            task_id="test-123",
            request_type="background",
            priority=RequestPriority.NORMAL,
            tokens_used=100,
            requests_used=1,
            success=True,
            latency_ms=150
        )

        # Act
        await storage.record_usage(entry)

        # Assert
        history = await storage.get_usage_history(hours=1)
        assert len(history) == 1
        assert history[0].tokens_used == 100
        await storage.close()

    @pytest.mark.asyncio
    async def test_get_usage_by_hour(self, db_path):
        # Arrange
        from datetime import timedelta
        storage = SQLiteStorage(db_path)
        await storage.initialize()
        now = datetime.utcnow()
        for i in range(5):
            entry = UsageEntry(
                timestamp=now - timedelta(minutes=i*10),
                task_id=f"task-{i}",
                request_type="background",
                priority=RequestPriority.NORMAL,
                tokens_used=100,
                requests_used=1,
                success=True,
                latency_ms=100
            )
            await storage.record_usage(entry)

        # Act
        hourly = await storage.get_usage_by_hour(hours=1)

        # Assert
        assert hourly["total_tokens"] == 500
        assert hourly["total_requests"] == 5
        await storage.close()

    @pytest.mark.asyncio
    async def test_survives_close_and_reopen(self, db_path):
        # Arrange
        # Session 1
        storage1 = SQLiteStorage(db_path)
        await storage1.initialize()
        task = AITask(name="persistent", prompt="test")
        await storage1.save_task(task)
        await storage1.close()

        # Act
        # Session 2
        storage2 = SQLiteStorage(db_path)
        await storage2.initialize()
        loaded = await storage2.load_task(task.id)

        # Assert
        assert loaded is not None
        assert loaded.name == "persistent"
        await storage2.close()
