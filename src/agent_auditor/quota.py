"""
Quota tracking and prediction for Agent-Auditor-SDK.

Implements:
- UsageJournal: Tracks API usage history
- QuotaPredictor: Predicts safe budget for background tasks

Follows Constitution Principle IX: Predictable Scheduling.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from agent_auditor.models import QuotaBudget, TierLimits, UsageEntry

if TYPE_CHECKING:
    from agent_auditor.persistence.sqlite import SQLiteStorage


class UsageJournal:
    """
    Tracks API usage for quota management and prediction.

    Stores usage entries with timestamps for:
    - Current usage tracking (RPM, TPM, RPD)
    - Historical analysis for prediction

    Example:
        journal = UsageJournal()
        await journal.record_usage(entry)
        history = await journal.get_history(hours=1)
    """

    def __init__(self, storage: Optional["SQLiteStorage"] = None) -> None:
        """
        Initialize the usage journal.

        Args:
            storage: Optional SQLiteStorage for persistence.
        """
        self._storage = storage
        self._entries: list[UsageEntry] = []
        self._lock = asyncio.Lock()

        # Running totals for current day
        self._today = datetime.utcnow().date()
        self._requests_today = 0
        self._tokens_today = 0

    async def record_usage(self, entry: UsageEntry) -> None:
        """
        Record a usage entry.

        Args:
            entry: The UsageEntry to record.
        """
        async with self._lock:
            self._entries.append(entry)

            # Update running totals if same day
            entry_date = entry.timestamp.date()
            if entry_date == self._today:
                self._requests_today += entry.requests_used
                self._tokens_today += entry.tokens_used
            elif entry_date > self._today:
                # New day, reset totals
                self._today = entry_date
                self._requests_today = entry.requests_used
                self._tokens_today = entry.tokens_used

            # Persist if storage available
            if self._storage:
                await self._storage.record_usage(entry)

    async def get_history(self, hours: int = 24) -> list[UsageEntry]:
        """
        Get usage history for the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            List of UsageEntry within the time window.
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        async with self._lock:
            return [
                entry for entry in self._entries
                if entry.timestamp >= cutoff
            ]

    async def get_totals(self) -> dict:
        """Get running totals for all recorded entries."""
        async with self._lock:
            total_tokens = sum(e.tokens_used for e in self._entries)
            total_requests = sum(e.requests_used for e in self._entries)

            return {
                "total_tokens": total_tokens,
                "total_requests": total_requests
            }

    async def get_hourly_breakdown(self, hours: int = 1) -> dict:
        """
        Get aggregated usage for the last N hours.

        Returns:
            Dictionary with tokens, requests, and count.
        """
        history = await self.get_history(hours=hours)

        return {
            "tokens": sum(e.tokens_used for e in history),
            "requests": sum(e.requests_used for e in history),
            "count": len(history)
        }

    async def get_daily_usage(self) -> dict:
        """Get today's usage statistics."""
        await self._check_day_reset()

        async with self._lock:
            return {
                "requests_today": self._requests_today,
                "tokens_today": self._tokens_today,
                "date": self._today.isoformat()
            }

    async def _check_day_reset(self) -> None:
        """Reset totals if a new day has started."""
        today = datetime.utcnow().date()

        async with self._lock:
            if today > self._today:
                self._today = today
                self._requests_today = 0
                self._tokens_today = 0


class QuotaPredictor:
    """
    Predicts safe quota budget for background task execution.

    Implements Constitution Principle I: Human Priority is Non-Negotiable
    by reserving a portion of quota for human requests.

    Example:
        predictor = QuotaPredictor(tier_limits=limits)
        budget = await predictor.get_safe_budget()
        if budget.requests_available > 0:
            # Safe to queue background tasks
    """

    def __init__(
        self,
        tier_limits: Optional[TierLimits] = None,
        usage_journal: Optional[UsageJournal] = None,
        human_reserve_percent: int = 30
    ) -> None:
        """
        Initialize the quota predictor.

        Args:
            tier_limits: API rate limits (defaults to Free Tier).
            usage_journal: UsageJournal for current usage data.
            human_reserve_percent: Percentage to reserve for humans.
        """
        self.tier_limits = tier_limits or TierLimits()
        self.usage_journal = usage_journal or UsageJournal()
        self.human_reserve_percent = human_reserve_percent

    async def get_safe_budget(self) -> QuotaBudget:
        """
        Calculate safe quota budget for background tasks.

        Returns:
            QuotaBudget with available quota after human reserve.
        """
        # Get current daily usage
        daily = await self.usage_journal.get_daily_usage()
        requests_used = daily["requests_today"]
        tokens_used = daily["tokens_today"]

        # Calculate remaining quota
        requests_remaining = max(0, self.tier_limits.requests_per_day - requests_used)
        tokens_remaining = max(0, self.tier_limits.tokens_per_minute * 60 * 24 - tokens_used)

        # Apply human reserve
        reserve_factor = (100 - self.human_reserve_percent) / 100

        requests_available = int(requests_remaining * reserve_factor)
        tokens_available = int(tokens_remaining * reserve_factor)

        # Calculate confidence (higher with more history)
        history = await self.usage_journal.get_history(hours=24)
        confidence = min(1.0, 0.5 + len(history) * 0.01)

        return QuotaBudget(
            requests_available=requests_available,
            tokens_available=tokens_available,
            window_end=datetime.utcnow() + timedelta(hours=1),
            confidence=confidence,
            human_reserve_percent=self.human_reserve_percent
        )

    async def get_minute_budget(self) -> QuotaBudget:
        """Get budget for the current minute window (RPM/TPM)."""
        # Get minute window usage
        hourly = await self.usage_journal.get_hourly_breakdown(hours=1)

        # Simple estimate: divide hourly by 60
        requests_used_per_minute = hourly["requests"] / max(1, hourly["count"])

        # Calculate remaining
        requests_available = max(0, int(self.tier_limits.requests_per_minute - requests_used_per_minute))
        tokens_available = max(0, self.tier_limits.tokens_per_minute)

        return QuotaBudget(
            requests_available=requests_available,
            tokens_available=tokens_available,
            window_end=datetime.utcnow() + timedelta(minutes=1),
            confidence=0.7,
            human_reserve_percent=self.human_reserve_percent
        )


class HistoricalPatternAnalyzer:
    """
    Analyzes historical usage patterns for predictive quota management.

    Implements Issue #6 acceptance criteria:
    - Historical pattern analysis
    - Time-of-day awareness

    Example:
        analyzer = HistoricalPatternAnalyzer(journal)
        patterns = await analyzer.get_usage_patterns()
        peak_hours = patterns["peak_hours"]
    """

    def __init__(self, usage_journal: UsageJournal) -> None:
        """
        Initialize the pattern analyzer.

        Args:
            usage_journal: UsageJournal with historical data.
        """
        self.usage_journal = usage_journal

    async def get_hourly_distribution(self, days: int = 7) -> dict[int, dict]:
        """
        Get average usage distribution by hour of day.

        Args:
            days: Number of days of history to analyze.

        Returns:
            Dict mapping hour (0-23) to average usage stats.
        """
        history = await self.usage_journal.get_history(hours=days * 24)

        hourly_data: dict[int, list[UsageEntry]] = {h: [] for h in range(24)}

        for entry in history:
            hour = entry.timestamp.hour
            hourly_data[hour].append(entry)

        distribution = {}
        for hour, entries in hourly_data.items():
            if entries:
                distribution[hour] = {
                    "avg_requests": sum(e.requests_used for e in entries) / len(entries),
                    "avg_tokens": sum(e.tokens_used for e in entries) / len(entries),
                    "sample_count": len(entries),
                }
            else:
                distribution[hour] = {
                    "avg_requests": 0,
                    "avg_tokens": 0,
                    "sample_count": 0,
                }

        return distribution

    async def get_peak_hours(self, top_n: int = 3) -> list[int]:
        """
        Identify the top N hours with highest average usage.

        Args:
            top_n: Number of peak hours to return.

        Returns:
            List of hours (0-23) sorted by highest usage.
        """
        distribution = await self.get_hourly_distribution()

        sorted_hours = sorted(
            distribution.items(),
            key=lambda x: x[1]["avg_requests"],
            reverse=True
        )

        return [hour for hour, _ in sorted_hours[:top_n]]

    async def get_day_of_week_pattern(self) -> dict[int, dict]:
        """
        Get usage patterns by day of week (0=Monday, 6=Sunday).

        Returns:
            Dict mapping day of week to average usage stats.
        """
        history = await self.usage_journal.get_history(hours=7 * 24)

        daily_data: dict[int, list[UsageEntry]] = {d: [] for d in range(7)}

        for entry in history:
            day = entry.timestamp.weekday()
            daily_data[day].append(entry)

        pattern = {}
        for day, entries in daily_data.items():
            if entries:
                pattern[day] = {
                    "total_requests": sum(e.requests_used for e in entries),
                    "total_tokens": sum(e.tokens_used for e in entries),
                    "sample_count": len(entries),
                }
            else:
                pattern[day] = {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "sample_count": 0,
                }

        return pattern

    async def is_peak_time(self) -> bool:
        """
        Check if current time is typically a high-usage period.

        Returns:
            True if current hour is in top 3 peak hours.
        """
        peak_hours = await self.get_peak_hours(top_n=3)
        current_hour = datetime.utcnow().hour
        return current_hour in peak_hours

    async def get_usage_patterns(self) -> dict:
        """
        Get comprehensive usage pattern analysis.

        Returns:
            Dictionary with all pattern analyses.
        """
        return {
            "hourly_distribution": await self.get_hourly_distribution(),
            "peak_hours": await self.get_peak_hours(),
            "day_of_week_pattern": await self.get_day_of_week_pattern(),
            "is_currently_peak": await self.is_peak_time(),
        }


class TimeAwareQuotaPredictor(QuotaPredictor):
    """
    Enhanced quota predictor with time-of-day awareness.

    Adjusts background task budgets based on historical patterns,
    reducing allocation during peak hours to preserve human headroom.
    """

    def __init__(
        self,
        tier_limits: Optional[TierLimits] = None,
        usage_journal: Optional[UsageJournal] = None,
        human_reserve_percent: int = 30,
        peak_hour_reserve_boost: int = 20
    ) -> None:
        """
        Initialize time-aware predictor.

        Args:
            tier_limits: API rate limits.
            usage_journal: Usage history tracker.
            human_reserve_percent: Base reserve for humans.
            peak_hour_reserve_boost: Additional reserve during peak hours.
        """
        super().__init__(tier_limits, usage_journal, human_reserve_percent)
        self.peak_hour_reserve_boost = peak_hour_reserve_boost
        self.pattern_analyzer = HistoricalPatternAnalyzer(self.usage_journal)

    async def get_safe_budget(self) -> QuotaBudget:
        """
        Calculate time-aware safe quota budget.

        During peak hours, increases human reserve to protect against
        quota exhaustion when human demand is highest.
        """
        is_peak = await self.pattern_analyzer.is_peak_time()

        # Boost reserve during peak hours
        effective_reserve = self.human_reserve_percent
        if is_peak:
            effective_reserve = min(80, self.human_reserve_percent + self.peak_hour_reserve_boost)

        # Get current daily usage
        daily = await self.usage_journal.get_daily_usage()
        requests_used = daily["requests_today"]
        tokens_used = daily["tokens_today"]

        # Calculate remaining quota
        requests_remaining = max(0, self.tier_limits.requests_per_day - requests_used)
        tokens_remaining = max(0, self.tier_limits.tokens_per_minute * 60 * 24 - tokens_used)

        # Apply time-aware reserve
        reserve_factor = (100 - effective_reserve) / 100

        requests_available = int(requests_remaining * reserve_factor)
        tokens_available = int(tokens_remaining * reserve_factor)

        # Confidence based on history depth and peak accuracy
        history = await self.usage_journal.get_history(hours=24)
        confidence = min(1.0, 0.5 + len(history) * 0.01)
        if is_peak:
            confidence = min(confidence, 0.8)  # Lower confidence during peak

        return QuotaBudget(
            requests_available=requests_available,
            tokens_available=tokens_available,
            window_end=datetime.utcnow() + timedelta(hours=1),
            confidence=confidence,
            human_reserve_percent=effective_reserve
        )

    async def get_predicted_usage(self) -> dict:
        """
        Predict expected usage for the current hour based on patterns.

        Returns:
            Dictionary with predicted requests and tokens.
        """
        distribution = await self.pattern_analyzer.get_hourly_distribution()
        current_hour = datetime.utcnow().hour

        hour_stats = distribution.get(current_hour, {"avg_requests": 0, "avg_tokens": 0})

        return {
            "predicted_requests": hour_stats["avg_requests"],
            "predicted_tokens": hour_stats["avg_tokens"],
            "based_on_samples": hour_stats.get("sample_count", 0),
            "current_hour": current_hour,
        }
