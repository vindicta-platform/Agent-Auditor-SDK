from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RequestPriority(IntEnum):
    """
    Priority levels for task scheduling.
    """

    HUMAN = 0
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class AITask(BaseModel):
    """
    A task to be executed against an AI API.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(...)
    prompt: str = Field(...)
    model: str = Field(default="gemini-1.5-flash")
    priority: RequestPriority = Field(default=RequestPriority.NORMAL)
    estimated_tokens: int | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = Field(None, description="Group tasks into conversations")

    class Config:
        use_enum_values = True


class TaskResult(BaseModel):
    task_id: UUID
    status: Literal["success", "failed", "queued", "cancelled"]
    response: str | None = None
    error: str | None = None
    tokens_used: int = 0
    latency_ms: int = 0
    completed_at: datetime = Field(default_factory=datetime.utcnow)


@dataclass
class UsageEntry:
    timestamp: datetime
    task_id: str
    request_type: Literal["human", "background"]
    priority: RequestPriority
    tokens_used: int
    requests_used: int
    success: bool
    latency_ms: int
    error: str | None = None
    task_name: str = ""
    conversation_id: str | None = None
