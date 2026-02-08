from .archetypes import ArchetypeClassifier
from .context_cost import ContextTransferCostModel
from .decision_matrix import ModelDecisionEngine
from .models import (
    AnalysisReport,
    ConversationTurn,
    InflectionPoint,
    ModelRecommendation,
)
from .rewards import RewardConfig, RewardEvaluator


class ConversationAnalyzer:
    """
    Retrospective conversation analysis pipeline.
    Segments, classifies, scores, and reports on model selection optimization.
    """

    def __init__(
        self,
        engine: ModelDecisionEngine | None = None,
        reward_config: RewardConfig | None = None,
        classifier: ArchetypeClassifier | None = None,
    ):
        self.engine = engine or ModelDecisionEngine()
        self.evaluator = RewardEvaluator(self.engine, config=reward_config)
        self.classifier = classifier or ArchetypeClassifier()
        self.cost_model = ContextTransferCostModel()

    def analyze(self, conversation_id: str, turns: list[ConversationTurn]) -> AnalysisReport:
        """
        Runs the full retrospective analysis pipeline on a list of conversation turns.
        """
        inflection_points: list[InflectionPoint] = []
        actual_total_reward = 0.0
        optimal_total_reward = 0.0

        previous_model: str | None = None

        # First pass: Classify and Evaluate per-turn
        for i, turn in enumerate(turns):
            if turn.role != "user":
                continue  # We evaluate inflection points at user prompts

            # 1. Classify Archetype
            archetype, confidence = self.classifier.classify(turn.content)

            # 2. Score actual model used (if assistant responded after this user turn)
            model_used = None
            if i + 1 < len(turns) and turns[i + 1].role == "assistant":
                model_used = turns[i + 1].model

            has_tool_state = turn.metadata.get("has_tool_state", False)

            # 3. Calculate Actual Reward
            turn_actual_reward = 0.0
            if model_used:
                loss_ratio = (
                    self.cost_model.calculate_loss_ratio(previous_model, model_used, has_tool_state)
                    if previous_model
                    else 0.0
                )

                turn_actual_reward = self.evaluator.calculate_total_reward(
                    model_used, archetype, previous_model, loss_ratio
                )
                actual_total_reward += turn_actual_reward

            # 4. Find Optimal Model (Counterfactual)
            optimal_model = None
            max_reward = -1.0

            for candidate in self.engine.get_available_models():
                loss_ratio = (
                    self.cost_model.calculate_loss_ratio(previous_model, candidate, has_tool_state)
                    if previous_model
                    else 0.0
                )

                reward = self.evaluator.calculate_total_reward(
                    candidate, archetype, previous_model, loss_ratio
                )

                if reward > max_reward:
                    max_reward = reward
                    optimal_model = candidate

            optimal_total_reward += max_reward
            delta = max_reward - turn_actual_reward

            # 5. Record Inflection Point
            ip = InflectionPoint(
                turn_index=i,
                archetype=archetype,
                confidence=confidence,
                model_used=model_used,
                optimal_model=optimal_model,
                reward_score=turn_actual_reward,
                counterfactual_reward=max_reward,
                delta=delta,
                reasoning=f"Archetype {archetype} detected. Optimal reward via {optimal_model}.",
            )
            inflection_points.append(ip)

            # Update sequence: assume the used model was correct
            # for NEXT turn's switch cost calculation.
            previous_model = model_used or previous_model

        # 6. Build Switching Schedule
        schedule = [
            ModelRecommendation(
                turn_index=ip.turn_index,
                recommended_model=ip.optimal_model,
                confidence=ip.confidence,
                reasoning=f"Switch to {ip.optimal_model} for {ip.archetype} task optimization.",
                expected_reward=ip.counterfactual_reward,
            )
            for ip in inflection_points
            if ip.delta > 0.02  # Only recommend if delta is significant
        ]

        # 7. Summary Metrics
        report = AnalysisReport(
            conversation_id=conversation_id,
            total_turns=len(turns),
            inflection_points=inflection_points,
            actual_reward=actual_total_reward,
            optimal_reward=optimal_total_reward,
            potential_improvement=(1 - (actual_total_reward / optimal_total_reward)) * 100
            if optimal_total_reward > 0
            else 0,
            cost_savings_estimate=self._estimate_savings(inflection_points),
            switching_schedule=schedule,
        )

        return report

    def _estimate_savings(self, ips: list[InflectionPoint]) -> float:
        """Very rough estimation of token cost savings based on model tiers."""
        # This would be more accurate if we matched to actual pricing/quota tokens
        return sum(ip.delta for ip in ips) * 0.1  # Simplified index
