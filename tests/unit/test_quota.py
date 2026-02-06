"""
Unit tests for UsageJournal and QuotaPredictor.

Layer: Unit
Scope: Quota calculation and usage tracking logic.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from agent_auditor.quota import UsageJournal, QuotaPredictor, HistoricalPatternAnalyzer, TimeAwareQuotaPredictor
from agent_auditor.models import UsageEntry, RequestPriority, TierLimits


class TestUsageJournalRecordUsage:

    @pytest.mark.asyncio
    async def test_record_usage_stores_entry(self):
        # Arrange
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
        
        # Act
        await journal.record_usage(entry)
        
        # Assert
        history = await journal.get_history(hours=1)
        assert len(history) == 1
        assert history[0].task_id == "task-123"

    @pytest.mark.asyncio
    async def test_record_usage_tracks_totals(self):
        # Arrange
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
        
        # Act
        totals = await journal.get_totals()
        
        # Assert
        assert totals["total_tokens"] == 500
        assert totals["total_requests"] == 5


class TestUsageJournalGetHistory:

    @pytest.mark.asyncio
    async def test_get_history_filters_by_hours(self):
        # Arrange
        journal = UsageJournal()
        now = datetime.utcnow()
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
        await journal.record_usage(recent)
        await journal.record_usage(old)
        
        # Act
        history = await journal.get_history(hours=1)
        
        # Assert
        assert len(history) == 1
        assert history[0].task_id == "recent"

    @pytest.mark.asyncio
    async def test_get_history_groups_by_hour(self):
        # Arrange
        journal = UsageJournal()
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
            await journal.record_usage(entry)
        
        # Act
        breakdown = await journal.get_hourly_breakdown(hours=1)
        
        # Assert
        assert breakdown["tokens"] == 500
        assert breakdown["requests"] == 5

    @pytest.mark.asyncio
    async def test_get_daily_usage(self):
        # Arrange
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
        
        # Act
        daily = await journal.get_daily_usage()
        
        # Assert
        assert daily["requests_today"] == 3
        assert daily["tokens_today"] == 3000


class TestQuotaPredictor:

    @pytest.mark.asyncio
    async def test_get_safe_budget_respects_human_reserve(self):
        # Arrange
        limits = TierLimits(
            requests_per_minute=15,
            tokens_per_minute=1_000_000,
            requests_per_day=1500
        )
        predictor = QuotaPredictor(tier_limits=limits, human_reserve_percent=30)
        
        # Act
        budget = await predictor.get_safe_budget()
        
        # Assert
        # 30% of 1500 = 450 reserved. Max available = 1050
        assert budget.requests_available <= 1050
        assert budget.human_reserve_percent == 30

    @pytest.mark.asyncio
    async def test_get_safe_budget_considers_current_usage(self):
        # Arrange
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
        
        # Act
        budget = await predictor.get_safe_budget()
        
        # Assert
        # 1500 daily - 500 used = 1000 remaining
        # 20% reserve = 200 for humans
        # Max for background = 800
        assert budget.requests_available <= 800

    @pytest.mark.asyncio
    async def test_get_safe_budget_returns_zero_when_exhausted(self):
        # Arrange
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
        
        # Act
        budget = await predictor.get_safe_budget()
        
        # Assert
        assert budget.requests_available == 0

    @pytest.mark.asyncio
    async def test_predictor_has_confidence_score(self):
        # Arrange
        limits = TierLimits()
        predictor = QuotaPredictor(tier_limits=limits)
        
        # Act
        budget = await predictor.get_safe_budget()
        
        # Assert
        assert 0.0 <= budget.confidence <= 1.0


class TestHistoricalPatternAnalyzer:
    """Tests for Issue #6: Historical pattern analysis."""

    @pytest.mark.asyncio
    async def test_get_hourly_distribution_returns_24_hours(self):
        # Arrange
        journal = UsageJournal()
        analyzer = HistoricalPatternAnalyzer(journal)
        
        # Act
        distribution = await analyzer.get_hourly_distribution()
        
        # Assert
        assert len(distribution) == 24
        for hour in range(24):
            assert hour in distribution

    @pytest.mark.asyncio
    async def test_get_peak_hours_returns_sorted_list(self):
        # Arrange
        journal = UsageJournal()
        now = datetime.utcnow()
        
        # Add more usage at hour 14
        for i in range(10):
            entry = UsageEntry(
                timestamp=now.replace(hour=14, minute=i),
                task_id=f"peak-{i}",
                request_type="background",
                priority=RequestPriority.NORMAL,
                tokens_used=100,
                requests_used=10,  # High usage
                success=True,
                latency_ms=100
            )
            await journal.record_usage(entry)
        
        analyzer = HistoricalPatternAnalyzer(journal)
        
        # Act
        peak_hours = await analyzer.get_peak_hours(top_n=3)
        
        # Assert
        assert len(peak_hours) <= 3
        assert 14 in peak_hours  # Hour 14 should be peak

    @pytest.mark.asyncio
    async def test_get_day_of_week_pattern_returns_7_days(self):
        # Arrange
        journal = UsageJournal()
        analyzer = HistoricalPatternAnalyzer(journal)
        
        # Act
        pattern = await analyzer.get_day_of_week_pattern()
        
        # Assert
        assert len(pattern) == 7
        for day in range(7):
            assert day in pattern

    @pytest.mark.asyncio
    async def test_get_usage_patterns_returns_complete_analysis(self):
        # Arrange
        journal = UsageJournal()
        analyzer = HistoricalPatternAnalyzer(journal)
        
        # Act
        patterns = await analyzer.get_usage_patterns()
        
        # Assert
        assert "hourly_distribution" in patterns
        assert "peak_hours" in patterns
        assert "day_of_week_pattern" in patterns
        assert "is_currently_peak" in patterns


class TestTimeAwareQuotaPredictor:
    """Tests for Issue #6: Time-of-day awareness in quota prediction."""

    @pytest.mark.asyncio
    async def test_time_aware_predictor_has_pattern_analyzer(self):
        # Arrange
        predictor = TimeAwareQuotaPredictor()
        
        # Assert
        assert hasattr(predictor, "pattern_analyzer")
        assert isinstance(predictor.pattern_analyzer, HistoricalPatternAnalyzer)

    @pytest.mark.asyncio
    async def test_peak_hour_reserve_boost_increases_reserve(self):
        # Arrange
        limits = TierLimits(requests_per_day=1500)
        predictor = TimeAwareQuotaPredictor(
            tier_limits=limits,
            human_reserve_percent=30,
            peak_hour_reserve_boost=20
        )
        
        # Assert
        assert predictor.peak_hour_reserve_boost == 20
        assert predictor.human_reserve_percent == 30

    @pytest.mark.asyncio
    async def test_get_predicted_usage_returns_hour_stats(self):
        # Arrange
        journal = UsageJournal()
        predictor = TimeAwareQuotaPredictor(usage_journal=journal)
        
        # Act
        predicted = await predictor.get_predicted_usage()
        
        # Assert
        assert "predicted_requests" in predicted
        assert "predicted_tokens" in predicted
        assert "current_hour" in predicted
        assert 0 <= predicted["current_hour"] <= 23

