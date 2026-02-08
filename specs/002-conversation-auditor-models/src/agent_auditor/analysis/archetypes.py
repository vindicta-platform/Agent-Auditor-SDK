import re

from .models import ClassificationMiss, TaskArchetype


class ArchetypeClassifier:
    """
    Heuristic-based classifier for mapping prompts to TaskArchetypes.
    Includes miss logging for continuous improvement.
    """

    # Primary signal patterns (RegEx)
    SIGNALS = {
        TaskArchetype.PLANNING: [
            r"\b(design|propose|plan|outline|architecture|roadmap|strategy)\b",
            r"\b(how should i approach)\b",
        ],
        TaskArchetype.CODE_GEN: [
            r"\b(write|create|implement|generate|boilerplate|coding|scaffold)\b.*\b(code|function|class|script|module|implementation|algorithm|utility)\b",
            r"\b(create a new)\b.*\b(file|project|app)\b",
        ],
        TaskArchetype.CODE_EDIT: [
            r"\b(fix|refactor|update|modify|change|add to|debug|optimize|patch|cleanup)\b",
            r"\b(in this file|at line|this block|refactor this)\b",
        ],
        TaskArchetype.REASONING: [
            r"\b(analyze|compare|evaluate|contrast|why|logical|proof|derivation|paradox|rationale|theory)\b",
            r"\b(what are the trade-offs)\b",
        ],
        TaskArchetype.SEARCH: [
            r"\b(find|search|lookup|grep|locate|where is)\b",
            r"\b(list all instances of)\b",
        ],
        TaskArchetype.REVIEW: [
            r"\b(review|audit|check|verify|inspect|validate)\b",
            r"\b(is this correct|summarize changes)\b",
        ],
        TaskArchetype.CHAT: [
            r"\b(what is|how do i|tell me about|who is|meaning of)\b",
            r"^(hi|hello|thanks|thank you|ok|yes|no)$",
        ],
    }

    def __init__(self, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold
        self.miss_journal: list[ClassificationMiss] = []

    def classify(self, prompt: str) -> tuple[TaskArchetype, float]:
        """
        Classifies a prompt into an archetype based on signal strength.
        """
        prompt_lower = prompt.lower()
        scores = {archetype: 0 for archetype in TaskArchetype}

        for archetype, patterns in self.SIGNALS.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    scores[archetype] += 1

        if not any(scores.values()):
            return TaskArchetype.UNKNOWN, 0.0

        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_archetype, top_score = sorted_scores[0]

        # Calculate confidence (very simple: relative strength)
        total_score = sum(scores.values())
        confidence = top_score / total_score if total_score > 0 else 0.0

        # Log miss if low confidence
        if confidence < self.confidence_threshold:
            self._log_miss(prompt, top_archetype, confidence)

        return top_archetype, confidence

    def _log_miss(self, prompt: str, predicted: TaskArchetype, confidence: float):
        """
        Logs a classification miss for future labeling/improvement.
        """
        snippet = prompt[:100] + "..." if len(prompt) > 100 else prompt
        miss = ClassificationMiss(
            prompt_snippet=snippet, predicted_archetype=predicted, confidence=confidence
        )
        self.miss_journal.append(miss)

    def get_misses(self) -> list[ClassificationMiss]:
        """Returns the current scroll of classification misses."""
        return self.miss_journal

    def clear_misses(self):
        """Clears the miss journal."""
        self.miss_journal = []
