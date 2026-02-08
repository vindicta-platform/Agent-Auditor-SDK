class ContextTransferCostModel:
    """
    Quantifies the penalty for mid-conversation model switching.
    """

    def calculate_loss_ratio(
        self, from_model: str, to_model: str, has_tool_state: bool = False
    ) -> float:
        """
        Estimates the context_loss_ratio [0.0 - 1.0] based on transition types.
        """
        if from_model == to_model:
            return 0.0

        # Determine provider mismatch
        from_provider = self._get_provider(from_model)
        to_provider = self._get_provider(to_model)

        ratio = 0.05  # Base penalty for tier switch (e.g. Pro -> Flash)

        if from_provider != to_provider:
            ratio += 0.15  # Additional penalty for cross-provider (format translation)

        if has_tool_state:
            ratio += 0.10  # Additional penalty for tool call state re-initialization

        return min(0.4, ratio)  # Cap at 40% loss representation

    def _get_provider(self, model_name: str) -> str:
        name = model_name.lower()
        if "gemini" in name:
            return "google"
        if "claude" in name:
            return "anthropic"
        if "gpt" in name:
            return "openai"
        if "oss" in name or "mistral" in name:
            return "hf"
        return "unknown"

    def estimate_latency_penalty_ms(self, loss_ratio: float) -> int:
        """Heuristic for added latency due to context re-injection."""
        return int(loss_ratio * 4000)  # e.g. 0.25 -> 1000ms
