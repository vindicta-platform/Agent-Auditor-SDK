"""
Core data models for Agent-Auditor-SDK.

All models use Pydantic for validation and serialization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RequestPriority(IntEnum):
    """
    Priority levels for task scheduling.
    
    Lower values = higher priority.
    P0 (HUMAN) always preempts all other priorities.
    """
    
    HUMAN = 0       # Interactive requests - immediate, preempts everything
    CRITICAL = 1    # Rule-Sage audits, validation
    HIGH = 2        # Active debates, time-sensitive
    NORMAL = 3      # Standard batch processing
    LOW = 4         # Exploratory work, nice-to-have
    BACKGROUND = 5  # Training runs, analytics - lowest priority


class AITask(BaseModel):
    """
    A task to be executed against an AI API.
    
    Tasks are queued and executed based on priority and available quota.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    name: str = Field(..., description="Human-readable task name")
    prompt: str = Field(..., description="The prompt/payload to send")
    model: str = Field(default="gemini-1.5-flash", description="Target model")
    priority: RequestPriority = Field(
        default=RequestPriority.NORMAL, 
        description="Task priority level"
    )
    estimated_tokens: Optional[int] = Field(
        default=None, 
        description="Estimated token count for proactive rate limiting"
    )
    history: List[Dict[str, str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class TaskResult(BaseModel):
    """
    Result of an executed AI task.
    """
    
    task_id: UUID
    status: Literal["success", "failed", "queued", "cancelled"]
    response: str | None = None
    error: str | None = None
    tokens_used: int = 0
    latency_ms: int = 0
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class QuotaBudget(BaseModel):
    """
    Available quota budget for a time window.
    
    Returned by QuotaPredictor to inform scheduling decisions.
    """
    
    requests_available: int = Field(ge=0, description="Requests available this window")
    tokens_available: int = Field(ge=0, description="Tokens available this window")
    window_end: datetime = Field(description="When this budget expires")
    confidence: float = Field(
        ge=0.0, le=1.0, 
        default=0.8, 
        description="Prediction confidence"
    )
    human_reserve_percent: int = Field(
        default=20,
        ge=0, le=100,
        description="Percentage reserved for human requests"
    )


@dataclass
class UsageEntry:
    """
    A single API usage log entry.
    
    Stored in the UsageJournal for prediction and auditing.
    IMPORTANT: Never log API keys or sensitive payloads.
    """
    
    timestamp: datetime
    task_id: str
    request_type: Literal["human", "background"]
    priority: RequestPriority
    tokens_used: int
    requests_used: int
    success: bool
    latency_ms: int
    error: str | None = None
    # Security: task_name only, never log prompts or keys
    task_name: str = ""


@dataclass 
class TierLimits:
    """
    API tier rate limits.
    
    Defaults to Gemini Free Tier limits.
    """
    
    requests_per_minute: int = 15      # RPM
    tokens_per_minute: int = 1_000_000  # TPM
    requests_per_day: int = 1500       # RPD
    tier_name: str = "free"
