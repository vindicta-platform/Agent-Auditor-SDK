from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskArchetype(str, Enum):
    """
    Task archetypes for model selection optimization.
    """

    PLANNING = "PLANNING"
    CODE_GEN = "CODE_GEN"
    CODE_EDIT = "CODE_EDIT"
    REASONING = "REASONING"
    SEARCH = "SEARCH"
    REVIEW = "REVIEW"
    CHAT = "CHAT"
    MULTI_STEP = "MULTI_STEP"
    UNKNOWN = "UNKNOWN"


class ConversationTurn(BaseModel):
    """
    A single turn in a conversation.
    """

    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="The message content")
    model: str | None = Field(None, description="Model used for this turn (if assistant)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InflectionPoint(BaseModel):
    """
    A turn annotated with analysis metadata.
    """

    turn_index: int
    archetype: TaskArchetype
    confidence: float
    model_used: str | None
    optimal_model: str | None = None
    reward_score: float = 0.0
    counterfactual_reward: float = 0.0
    delta: float = 0.0
    reasoning: str | None = None


class ModelRecommendation(BaseModel):
    """
    Recommendation for a specific turn.
    """

    turn_index: int
    recommended_model: str
    confidence: float
    reasoning: str
    expected_reward: float


class AnalysisReport(BaseModel):
    """
    The full conversation analysis output.
    """

    conversation_id: str
    total_turns: int
    inflection_points: list[InflectionPoint]
    optimal_reward: float
    actual_reward: float
    potential_improvement: float  # Percentage
    cost_savings_estimate: float
    switching_schedule: list[ModelRecommendation]
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class ClassificationMiss(BaseModel):
    """
    Logged when archetype classification is low-confidence.
    Used for the 'Improvement Journal'.
    """

    id: UUID = Field(default_factory=uuid4)
    prompt_snippet: str
    predicted_archetype: TaskArchetype
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    corrected_archetype: TaskArchetype | None = None
