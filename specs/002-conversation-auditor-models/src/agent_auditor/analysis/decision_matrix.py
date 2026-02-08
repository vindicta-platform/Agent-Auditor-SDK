from pydantic import BaseModel, Field, field_validator

from .models import TaskArchetype


class ModelCapabilityScore(BaseModel):
    """
    Strongly typed capability score for a single model across key dimensions.
    All scores are normalized to [0.0, 1.0].
    """

    quality: float = Field(ge=0.0, le=1.0)
    speed: float = Field(ge=0.0, le=1.0)
    cost: float = Field(ge=0.0, le=1.0)
    context_window: int = Field(ge=0)
    tool_use: float = Field(ge=0.0, le=1.0)
    code: float = Field(ge=0.0, le=1.0)


class DecisionMatrixConfig(BaseModel):
    """
    Configuration for the model decision matrix.
    Supports injection of alternate matrices.
    """

    models: dict[str, ModelCapabilityScore]
    archetype_weights: dict[TaskArchetype, dict[str, float]]

    @field_validator("archetype_weights")
    @classmethod
    def validate_weights(cls, v: dict[TaskArchetype, dict[str, float]]):
        required_dimensions = {"quality", "speed", "cost", "tool_use", "code"}
        for archetype, dims in v.items():
            missing = required_dimensions - set(dims.keys())
            if missing:
                raise ValueError(f"Archetype {archetype} missing dimension weights: {missing}")
        return v


# DEFAULT_SEED_DATA
DEFAULT_MODELS = {
    "gemini-2.5-pro": ModelCapabilityScore(
        quality=0.95, speed=0.50, cost=0.30, context_window=1000000, tool_use=0.95, code=0.95
    ),
    "gemini-2.5-flash": ModelCapabilityScore(
        quality=0.85, speed=0.85, cost=0.70, context_window=1000000, tool_use=0.90, code=0.85
    ),
    "gemini-2.0-flash": ModelCapabilityScore(
        quality=0.75, speed=0.90, cost=0.85, context_window=1000000, tool_use=0.80, code=0.75
    ),
    "claude-4-opus": ModelCapabilityScore(
        quality=0.95, speed=0.45, cost=0.20, context_window=200000, tool_use=0.90, code=0.95
    ),
    "claude-4-sonnet": ModelCapabilityScore(
        quality=0.90, speed=0.75, cost=0.55, context_window=200000, tool_use=0.90, code=0.90
    ),
    "oss-120b": ModelCapabilityScore(
        quality=0.75, speed=0.70, cost=0.95, context_window=128000, tool_use=0.60, code=0.70
    ),
}

# Example Weights: archetype -> dimension -> multiplier
DEFAULT_ARCHETYPE_WEIGHTS = {
    TaskArchetype.PLANNING: {
        "quality": 1.0,
        "speed": 0.4,
        "cost": 0.3,
        "tool_use": 0.5,
        "code": 0.2,
    },
    TaskArchetype.CODE_GEN: {
        "quality": 0.9,
        "speed": 0.5,
        "cost": 0.4,
        "tool_use": 0.8,
        "code": 1.0,
    },
    TaskArchetype.CODE_EDIT: {
        "quality": 0.8,
        "speed": 0.6,
        "cost": 0.5,
        "tool_use": 0.7,
        "code": 1.0,
    },
    TaskArchetype.REASONING: {
        "quality": 1.0,
        "speed": 0.3,
        "cost": 0.2,
        "tool_use": 0.6,
        "code": 0.5,
    },
    TaskArchetype.SEARCH: {"quality": 0.6, "speed": 1.0, "cost": 0.8, "tool_use": 1.0, "code": 0.2},
    TaskArchetype.REVIEW: {"quality": 0.9, "speed": 0.5, "cost": 0.5, "tool_use": 0.4, "code": 0.9},
    TaskArchetype.CHAT: {"quality": 0.5, "speed": 1.0, "cost": 1.0, "tool_use": 0.2, "code": 0.1},
    TaskArchetype.MULTI_STEP: {
        "quality": 0.8,
        "speed": 0.6,
        "cost": 0.4,
        "tool_use": 1.0,
        "code": 0.7,
    },
    TaskArchetype.UNKNOWN: {
        "quality": 0.7,
        "speed": 0.7,
        "cost": 0.7,
        "tool_use": 0.7,
        "code": 0.7,
    },
}


class ModelDecisionEngine:
    """
    Engine that evaluates model performance against task archetypes
    using a strongly-typed decision matrix.
    """

    def __init__(self, config: DecisionMatrixConfig | None = None):
        self.config = config or DecisionMatrixConfig(
            models=DEFAULT_MODELS, archetype_weights=DEFAULT_ARCHETYPE_WEIGHTS
        )

    def score_model(self, model_name: str, archetype: TaskArchetype) -> float:
        """
        Calculates a raw score for a model on a specific archetype.
        Note: This is an internal component for the RewardEvaluator.
        """
        if model_name not in self.config.models:
            return 0.0

        model = self.config.models[model_name]
        weights = self.config.archetype_weights.get(
            archetype, DEFAULT_ARCHETYPE_WEIGHTS[TaskArchetype.UNKNOWN]
        )

        score = (
            model.quality * weights["quality"]
            + model.speed * weights["speed"]
            + model.cost * weights["cost"]
            + model.tool_use * weights["tool_use"]
            + model.code * weights["code"]
        )

        # Normalize by max possible score (sum of weights)
        total_weight = sum(weights.values())
        return score / total_weight if total_weight > 0 else 0.0

    def get_available_models(self) -> list[str]:
        return list(self.config.models.keys())

    def get_model_capabilities(self, model_name: str) -> ModelCapabilityScore | None:
        return self.config.models.get(model_name)
