"""
Quota prediction interface for Agent-Auditor-SDK.

Defines the interface for quota prediction per Issue #6.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class QuotaPrediction:
    """Predicted quota usage for a time period."""
    predicted_usage: int
    safe_budget: int
    confidence: float
    period_start: datetime
    period_end: datetime
    reasoning: Optional[str] = None


@dataclass
class UsagePattern:
    """Historical usage pattern."""
    hour_of_day: int
    day_of_week: int
    avg_usage: float
    peak_usage: int
    sample_count: int


class QuotaPredictor(ABC):
    """Abstract interface for quota prediction."""

    @abstractmethod
    def predict(self, horizon_hours: int = 24) -> QuotaPrediction:
        """Predict quota usage for the next N hours."""
        pass

    @abstractmethod
    def get_safe_budget(self) -> int:
        """Calculate safe budget for current period."""
        pass

    @abstractmethod
    def get_patterns(self) -> list[UsagePattern]:
        """Get historical usage patterns."""
        pass
