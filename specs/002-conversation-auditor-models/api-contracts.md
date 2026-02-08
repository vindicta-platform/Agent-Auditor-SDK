# API Contracts: Conversation Auditor Models

**Feature**: 002-conversation-auditor-models
**Created**: 2026-02-07

## Public API Surface

### Module: `agent_auditor.analysis`

All public classes and functions exported from `src/agent_auditor/analysis/__init__.py`.

---

### ConversationAnalyzer

**Purpose**: Orchestrates the full retrospective analysis pipeline.

```python
class ConversationAnalyzer:
    """Retrospective conversation analysis pipeline."""

    def __init__(
        self,
        classifier: Optional[ArchetypeClassifier] = None,
        decision_engine: Optional[ModelDecisionEngine] = None,
        reward_evaluator: Optional[RewardEvaluator] = None,
        context_cost_model: Optional[ContextTransferCostModel] = None,
    ) -> None: ...

    def analyze(
        self,
        conversation_id: str,
        turns: List[ConversationTurn],
    ) -> AnalysisReport: ...
```

**Contract**:
- Input: Non-empty list of `ConversationTurn` objects
- Output: Complete `AnalysisReport` with inflection points and switching schedule
- Side effects: None (pure analysis)
- Thread safety: Safe for concurrent calls (no shared mutable state)
- Raises: `ValueError` if `turns` is empty

---

### ArchetypeClassifier

**Purpose**: Classifies user prompts into task archetypes using heuristic patterns.

```python
class ArchetypeClassifier:
    """Regex-based prompt archetype classifier."""

    def __init__(
        self,
        confidence_threshold: float = 0.4,
    ) -> None: ...

    def classify(
        self,
        prompt: str,
    ) -> Tuple[TaskArchetype, float]: ...

    @property
    def misses(self) -> List[ClassificationMiss]: ...
```

**Contract**:
- Input: Non-empty prompt string
- Output: Tuple of `(TaskArchetype, confidence)` where confidence ∈ [0.0, 1.0]
- Low-confidence predictions (< threshold) are logged to `misses`
- Deterministic: Same prompt always produces same classification

---

### ModelDecisionEngine

**Purpose**: Scores models against task archetypes using a capability matrix.

```python
class ModelDecisionEngine:
    """Decision matrix scoring engine."""

    def __init__(
        self,
        config: Optional[DecisionMatrixConfig] = None,
    ) -> None: ...

    def score_model(
        self,
        model_name: str,
        archetype: TaskArchetype,
    ) -> float: ...

    def get_optimal_model(
        self,
        archetype: TaskArchetype,
    ) -> Tuple[str, float]: ...

    def list_models(self) -> List[str]: ...
```

**Contract**:
- `score_model`: Returns normalized score ∈ [0.0, 1.0]. Unknown models return 0.0.
- `get_optimal_model`: Returns `(model_name, score)` for the highest-scoring model for the given archetype
- All operations are O(n) where n = number of registered models

---

### RewardEvaluator

**Purpose**: Calculates composite reward scores for model selections.

```python
class RewardEvaluator:
    """Multi-objective reward function calculator."""

    def __init__(
        self,
        config: Optional[RewardConfig] = None,
        decision_engine: Optional[ModelDecisionEngine] = None,
    ) -> None: ...

    def calculate_quality_reward(
        self,
        model_name: str,
        archetype: TaskArchetype,
    ) -> float: ...

    def calculate_efficiency_reward(
        self,
        model_name: str,
    ) -> float: ...

    def calculate_context_reward(
        self,
        previous_model: Optional[str],
        current_model: str,
        context_loss_ratio: float = 0.0,
    ) -> float: ...

    def calculate_total_reward(
        self,
        model_name: str,
        archetype: TaskArchetype,
        previous_model: Optional[str],
        context_loss_ratio: float = 0.0,
    ) -> float: ...
```

**Contract**:
- All reward components return values ∈ [0.0, 1.0]
- `calculate_total_reward` = weighted sum of R1 + R2 + R3
- `context_loss_ratio` must be ∈ [0.0, 1.0]

---

### ContextTransferCostModel

**Purpose**: Quantifies the penalty for mid-conversation model switching.

```python
class ContextTransferCostModel:
    """Context loss heuristic calculator."""

    def calculate_loss_ratio(
        self,
        from_model: str,
        to_model: str,
        has_tool_state: bool = False,
    ) -> float: ...
```

**Contract**:
- Returns loss ratio ∈ [0.0, 0.4] (capped)
- Same-provider switches incur lower cost than cross-provider
- `has_tool_state=True` adds tool state re-initialization penalty

---

## CLI Contract

### `analyze` Subcommand

```
python -m agent_auditor analyze --file <transcript.json> [--format text|json]
```

| Argument | Type   | Required | Default | Description             |
| -------- | ------ | -------- | ------- | ----------------------- |
| --file   | path   | Yes      | —       | Path to transcript JSON |
| --format | choice | No       | text    | Output format           |

**Transcript JSON Schema** (input):

```json
{
  "conversation_id": "string",
  "turns": [
    {
      "role": "user | assistant",
      "content": "string",
      "model": "string | null",
      "timestamp": "ISO 8601",
      "metadata": {}
    }
  ]
}
```

**JSON Output Schema** (when `--format json`): Serialized `AnalysisReport` model.

---

## Modified Existing Contracts

### UsageEntry (models.py)

```diff
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
+   conversation_id: str | None = None
```

### UsageJournal

```python
# New method
def query_by_conversation(
    self,
    conversation_id: str,
) -> List[UsageEntry]: ...
```
