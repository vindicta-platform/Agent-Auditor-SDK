from pydantic import BaseModel

from .decision_matrix import ModelDecisionEngine
from .models import TaskArchetype


class RewardConfig(BaseModel):
    """
    Global configuration for composite reward weights.
    """

    w_quality: float = 0.5
    w_efficiency: float = 0.3
    w_context: float = 0.2

    alpha_speed: float = 0.4  # Efficiency component weight (speed)
    beta_cost: float = 0.6  # Efficiency component weight (cost)

    gamma_context_penalty: float = 0.3  # Severity of context loss


class RewardEvaluator:
    """
    Calculates rewards for model selections at specific inflection points.
    """

    def __init__(self, engine: ModelDecisionEngine, config: RewardConfig | None = None):
        self.engine = engine
        self.config = config or RewardConfig()

    def calculate_quality_reward(self, model_name: str, archetype: TaskArchetype) -> float:
        """R1 - Based on model capability matrix calibrated for archetype."""
        return self.engine.score_model(model_name, archetype)

    def calculate_efficiency_reward(self, model_name: str) -> float:
        """R2 - Based on speed vs cost balance."""
        capabilities = self.engine.get_model_capabilities(model_name)
        if not capabilities:
            return 0.0

        return (
            self.config.alpha_speed * capabilities.speed + self.config.beta_cost * capabilities.cost
        )

    def calculate_context_reward(
        self, previous_model: str | None, current_model: str, context_loss_ratio: float = 0.0
    ) -> float:
        """R3 - Penalizes switching mid-conversation."""
        if previous_model is None or previous_model == current_model:
            return 1.0  # Full reward if no switch or start of conversation

        # Penalty depends on how much context is "lost" or needs re-injection
        return max(0.0, 1.0 - (self.config.gamma_context_penalty * context_loss_ratio))

    def calculate_total_reward(
        self,
        model_name: str,
        archetype: TaskArchetype,
        previous_model: str | None,
        context_loss_ratio: float = 0.0,
    ) -> float:
        """
        Composite reward: R_total = w1*R1 + w2*R2 + w3*R3
        """
        r1 = self.calculate_quality_reward(model_name, archetype)
        r2 = self.calculate_efficiency_reward(model_name)
        r3 = self.calculate_context_reward(previous_model, model_name, context_loss_ratio)

        total = (
            self.config.w_quality * r1 + self.config.w_efficiency * r2 + self.config.w_context * r3
        )
        return total
