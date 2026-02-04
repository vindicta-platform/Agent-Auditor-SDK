"""
Unit tests for UsageJournal and QuotaPredictor.

These tests MUST FAIL until quota.py is implemented.

Tests:
- T200-T202: UsageJournal
- T210-T212: QuotaPredictor
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock


class TestUsageJournalRecordUsage:
    """T200: Tests for UsageJournal.record_usage()"""

    @pytest.mark.asyncio
    async def test_record_usage_stores_entry(self):
        """record_usage() should store a usage entry."""
        from agent_auditor.quota import UsageJournal
        from agent_auditor.models import UsageEntry, RequestPriority
        
        journal = UsageJournal()
        
        entry = UsageEntry(
            timestamp=datetime.utcnow(),
            task_id="task-123",
            request_type="background",
            priority=RequestPriority.NORMAL,
            tokens_used=100,
            requests_used=1,
            success=True,
            latency_ms=150
        )
        
        await journal.record_usage(entry)
        
        history = await journal.get_history(hours=1)
        assert len(history) == 1
        assert history[0].task_id == "task-123"

    @pytest.mark.asyncio
    async def test_record_usage_tracks_totals(self):
        """record_usage() should update running totals."""
        from agent_auditor.quota import UsageJournal
        from agent_auditor.models import UsageEntry, RequestPriority
        
        journal = UsageJournal()
        
        for i in range(5):
            entry = UsageEntry(
                timestamp=datetime.utcnow(),
                task_id=f"task-{i}",
                request_type="background",
                priority=RequestPriority.NORMAL,
                tokens_used=100,
                requests_used=1,
                success=True,
                latency_ms=100
            )
            await journal.record_usage(entry)
        
        totals = await journal.get_totals()
        
        assert totals["total_tokens"] == 500
        assert totals["total_requests"] == 5


class TestUsageJournalGetHistory:
    """T201: Tests for UsageJournal.get_history()"""

    @pytest.mark.asyncio
    async def test_get_history_filters_by_hours(self):
        """get_history() should filter by time window."""
        from agent_auditor.quota import UsageJournal
        from agent_auditor.models import UsageEntry, RequestPriority
        
        journal = UsageJournal()
        
        # Add entries at different times
        now = datetime.utcnow()
        
        # Recent entry (within 1 hour)
        recent = UsageEntry(
            timestamp=now - timedelta(minutes=30),
            task_id="recent",
            request_type="background",
            priority=RequestPriority.NORMAL,
            tokens_used=100,
            requests_used=1,
            success=True,
            latency_ms=100
        )
        await journal.record_usage(recent)
        
        # Old entry (outside 1 hour, if journal tracks it)
        old = UsageEntry(
            timestamp=now - timedelta(hours=2),
            task_id="old",
            request_type="background",
            priority=RequestPriority.NORMAL,
            tokens_used=100,
            requests_used=1,
            success=True,
            latency_ms=100
        )
        await journal.record_usage(old)
        
        # Get last hour only
        history = await journal.get_history(hours=1)
        
        # Only recent should be in 1-hour window
        assert len(history) == 1
        assert history[0].task_id == "recent"

    @pytest.mark.asyncio
    async def test_get_history_groups_by_hour(self):
        """get_hourly_breakdown() should aggregate by hour."""
        from agent_auditor.quota import UsageJournal
        from agent_auditor.models import UsageEntry, RequestPriority
        
        journal = UsageJournal()
        
        now = datetime.utcnow()
        
        # Add 5 entries in current hour
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
            await journal.record_usage(entry)
        
        breakdown = await journal.get_hourly_breakdown(hours=1)
        
        assert breakdown["tokens"] == 500
        assert breakdown["requests"] == 5

    @pytest.mark.asyncio
    async def test_get_daily_usage(self):
        """get_daily_usage() should track today's usage."""
        from agent_auditor.quota import UsageJournal
        from agent_auditor.models import UsageEntry, RequestPriority
        
        journal = UsageJournal()
        
        for i in range(3):
            entry = UsageEntry(
                timestamp=datetime.utcnow(),
                task_id=f"task-{i}",
                request_type="background",
                priority=RequestPriority.NORMAL,
                tokens_used=1000,
                requests_used=1,
                success=True,
                latency_ms=100
            )
            await journal.record_usage(entry)
        
        daily = await journal.get_daily_usage()
        
        assert daily["requests_today"] == 3
        assert daily["tokens_today"] == 3000


class TestQuotaPredictor:
    """T210-T212: Tests for QuotaPredictor."""

    @pytest.mark.asyncio
    async def test_get_safe_budget_respects_human_reserve(self):
        """get_safe_budget() should reserve percentage for humans."""
        from agent_auditor.quota import QuotaPredictor
        from agent_auditor.models import TierLimits
        
        limits = TierLimits(
            requests_per_minute=15,
            tokens_per_minute=1_000_000,
            requests_per_day=1500
        )
        
        predictor = QuotaPredictor(tier_limits=limits, human_reserve_percent=30)
        
        budget = await predictor.get_safe_budget()
        
        # 30% of 1500 = 450 reserved for humans
        # Max available for background = 1050
        assert budget.requests_available <= 1050
        assert budget.human_reserve_percent == 30

    @pytest.mark.asyncio
    async def test_get_safe_budget_considers_current_usage(self):
        """get_safe_budget() should subtract current usage."""
        from agent_auditor.quota import QuotaPredictor, UsageJournal
        from agent_auditor.models import TierLimits, UsageEntry, RequestPriority
        
        limits = TierLimits(requests_per_day=1500)
        journal = UsageJournal()
        
        # Use 500 requests today
        for i in range(500):
            entry = UsageEntry(
                timestamp=datetime.utcnow(),
                task_id=f"task-{i}",
                request_type="background",
                priority=RequestPriority.NORMAL,
                tokens_used=100,
                requests_used=1,
                success=True,
                latency_ms=100
            )
            await journal.record_usage(entry)
        
        predictor = QuotaPredictor(
            tier_limits=limits,
            usage_journal=journal,
            human_reserve_percent=20
        )
        
        budget = await predictor.get_safe_budget()
        
        # 1500 daily - 500 used = 1000 remaining
        # 20% reserve = 200 for humans
        # Max for background = 800
        assert budget.requests_available <= 800

    @pytest.mark.asyncio
    async def test_get_safe_budget_returns_zero_when_exhausted(self):
        """get_safe_budget() should return 0 when quota exhausted."""
        from agent_auditor.quota import QuotaPredictor, UsageJournal
        from agent_auditor.models import TierLimits, UsageEntry, RequestPriority
        
        limits = TierLimits(requests_per_day=100)
        journal = UsageJournal()
        
        # Use all quota
        for i in range(100):
            entry = UsageEntry(
                timestamp=datetime.utcnow(),
                task_id=f"task-{i}",
                request_type="background",
                priority=RequestPriority.NORMAL,
                tokens_used=100,
                requests_used=1,
                success=True,
                latency_ms=100
            )
            await journal.record_usage(entry)
        
        predictor = QuotaPredictor(
            tier_limits=limits,
            usage_journal=journal
        )
        
        budget = await predictor.get_safe_budget()
        
        assert budget.requests_available == 0

    @pytest.mark.asyncio
    async def test_predictor_has_confidence_score(self):
        """QuotaPredictor should return confidence score."""
        from agent_auditor.quota import QuotaPredictor
        from agent_auditor.models import TierLimits
        
        limits = TierLimits()
        predictor = QuotaPredictor(tier_limits=limits)
        
        budget = await predictor.get_safe_budget()
        
        assert 0.0 <= budget.confidence <= 1.0
