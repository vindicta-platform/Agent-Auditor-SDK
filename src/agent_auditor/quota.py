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
