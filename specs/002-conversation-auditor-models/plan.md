# Implementation Plan: Conversation Auditor Models

**Feature**: 002-conversation-auditor-models
**Branch**: `002-conversation-auditor-models`
**Created**: 2026-02-07
**Spec Reference**: [spec.md](file:///c:/Users/bfoxt/vindicta-platform/Agent-Auditor-SDK/specs/002-conversation-auditor-models/spec.md)

## Technical Context

| Dimension           | Value                                                             |
| ------------------- | ----------------------------------------------------------------- |
| **Language**        | Python 3.11+                                                      |
| **Build System**    | Hatchling (`pyproject.toml`)                                      |
| **Package Manager** | `uv` (deterministic lockfile)                                     |
| **Data Modeling**   | Pydantic v2 (`BaseModel`, `Field`, `field_validator`)             |
| **Persistence**     | SQLite (std lib) via `UsageJournal`                               |
| **Test Framework**  | Pytest + pytest-asyncio (unit/component/functional/perf)          |
| **BDD Framework**   | Behave (features/functional, features/integration, features/live) |
| **Linting**         | Ruff (`line-length=100`, `target-version=py311`)                  |
| **Type Checking**   | Mypy (`strict=true`)                                              |
| **CI**              | GitHub Actions (`.github/workflows/ci.yml`)                       |

### Existing Integration Points

- **`src/agent_auditor/models.py`**: Core models (`AITask`, `RequestPriority`, `UsageEntry`, `TaskResult`). The `UsageEntry` dataclass needs a `conversation_id` field added.
- **`src/agent_auditor/__init__.py`**: Public API exports. Must be extended with analysis module exports.
- **`src/agent_auditor/__main__.py`**: CLI with `status`, `submit`, `process` commands. Must add `analyze` subcommand.
- **`src/agent_auditor/usage_journal.py`**: Persistence layer. Must add `query_by_conversation()` method.

## Constitution Check

| Principle                            | Status | Notes                                                              |
| ------------------------------------ | ------ | ------------------------------------------------------------------ |
| **MCP-First Mandate**                | ✅ N/A  | No cloud service interactions required                             |
| **Spec-Driven Development**          | ✅ Pass | SDD bundle: spec.md (complete), plan.md (this), tasks.md (pending) |
| **Economic Prime Directive**         | ✅ Pass | No external API calls; heuristic-only analysis, SQLite storage     |
| **Zero-Issue Stability**             | ✅ Pass | Additive feature, no breaking changes to existing API              |
| **Vanilla-Forward & Modern Tooling** | ✅ Pass | Standard Python stdlib + Pydantic, no new dependencies             |
| **Quality Gates**                    | ✅ Pass | Ruff, mypy strict, pytest with conftest fixtures                   |

## Architecture

### New Module: `src/agent_auditor/analysis/`

```
src/agent_auditor/analysis/
├── __init__.py           # Public exports
├── models.py             # TaskArchetype, ConversationTurn, InflectionPoint, AnalysisReport
├── archetypes.py         # ArchetypeClassifier (heuristic regex-based)
├── decision_matrix.py    # ModelCapabilityScore, DecisionMatrixConfig, ModelDecisionEngine
├── rewards.py            # RewardConfig, RewardEvaluator (R1/R2/R3 composite)
├── context_cost.py       # ContextTransferCostModel
└── analyzer.py           # ConversationAnalyzer (orchestration pipeline)
```

### Modified Files

| File                                 | Change Type | Description                                 |
| ------------------------------------ | ----------- | ------------------------------------------- |
| `src/agent_auditor/models.py`        | MODIFY      | Add `conversation_id` field to `UsageEntry` |
| `src/agent_auditor/__init__.py`      | MODIFY      | Export analysis module public API           |
| `src/agent_auditor/__main__.py`      | MODIFY      | Add `analyze` CLI subcommand                |
| `src/agent_auditor/usage_journal.py` | MODIFY      | Add `query_by_conversation()` method        |

### Data Flow

```
Transcript JSON → ConversationTurn[] → ConversationAnalyzer
  ├── ArchetypeClassifier.classify(prompt) → (TaskArchetype, confidence)
  ├── ModelDecisionEngine.score_model(model, archetype) → float
  ├── RewardEvaluator.calculate_total_reward() → composite score
  ├── ContextTransferCostModel.calculate_loss_ratio() → context penalty
  └── AnalysisReport (inflection points, rewards, switching schedule)
```

## Design Decisions

### D1: Heuristic Classification over ML

**Decision**: Use regex-based pattern matching for prompt classification.
**Rationale**: Avoids external ML dependencies, keeps the module self-contained within free-tier constraints (no inference calls needed for analysis). The miss journal enables iterative accuracy improvement.
**Alternatives**: LLM-based classification (rejected: costs quota), lightweight ML (rejected: adds model artifact management).

### D2: Composite Reward Function

**Decision**: `R_total = w_quality × R1 + w_efficiency × R2 + w_context × R3`
**Rationale**: Multi-objective optimization naturally captures the trade-off between quality, cost, and disruption. Weights are configurable for different operational priorities.
**Alternatives**: Single quality score (rejected: ignores cost/disruption), Pareto frontier (rejected: overly complex for v1).

### D3: Context Loss as Provider/Tier Heuristic

**Decision**: Approximate context loss via provider mismatch + tier difference + tool state flags.
**Rationale**: Empirical context measurement would require probe queries (costs quota). The heuristic model is sufficient for retrospective analysis and captures the primary cost drivers.
**Alternatives**: Probe-based measurement (rejected: uses quota), fixed penalty (rejected: ignores significant variation between same-provider and cross-provider switches).

### D4: Additive Integration (No Breaking Changes)

**Decision**: All changes are additive — new module, new CLI command, new UsageJournal method. No existing API signatures are modified.
**Rationale**: Zero-Issue Stability principle. Existing tests remain valid. The `conversation_id` field on `UsageEntry` defaults to `None` for backward compatibility.

## Libraries & Dependencies

**No new dependencies required.** The entire feature uses:
- `pydantic` (already in `dependencies`)
- `re` (stdlib)
- `sqlite3` (stdlib)
- `json` (stdlib)
- `argparse` (stdlib)

## Project Structure (Post-Implementation)

```
src/agent_auditor/
├── __init__.py            # [MODIFY] Add analysis exports
├── __main__.py            # [MODIFY] Add 'analyze' command
├── models.py              # [MODIFY] Add conversation_id to UsageEntry
├── usage_journal.py       # [MODIFY] Add query_by_conversation()
├── analysis/              # [NEW] Entire directory
│   ├── __init__.py
│   ├── models.py
│   ├── archetypes.py
│   ├── decision_matrix.py
│   ├── rewards.py
│   ├── context_cost.py
│   └── analyzer.py
├── adapters/
├── persistence/
├── scheduler.py
├── queue.py
├── worker.py
├── quota.py
├── rate_limiter.py
├── security.py
├── settings.py
├── errors.py
└── journal_schema.py

tests/
├── unit/
│   ├── test_archetypes.py       # [NEW]
│   ├── test_decision_matrix.py  # [NEW]
│   ├── test_rewards.py          # [NEW]
│   ├── test_context_cost.py     # [NEW]
│   └── test_analyzer.py         # [NEW]
├── component/
│   └── test_analysis_pipeline.py # [NEW]
└── conftest.py                   # [MODIFY] Add analysis fixtures
```

## Verification Plan

### Automated Tests

1. **Unit tests** (pytest): Each module tested independently with mock data
   - `test_archetypes.py`: Classification of known prompt patterns
   - `test_decision_matrix.py`: Model scoring with default and custom matrices
   - `test_rewards.py`: R1/R2/R3 individual + composite reward calculations
   - `test_context_cost.py`: Loss ratio for same-provider, cross-provider, tool-state scenarios
   - `test_analyzer.py`: Full pipeline with sample transcripts

2. **Component tests** (pytest): End-to-end pipeline integration
   - Transcript → Full Report with inflection points and schedule

3. **Linting & Types**:
   ```bash
   uv run ruff check src/agent_auditor/analysis/
   uv run mypy src/agent_auditor/analysis/
   ```

4. **CI**: Existing GitHub Actions workflow runs all tests on PR

### Manual Verification

- Run `python -m agent_auditor analyze --file sample_transcript.json` and verify human-readable output
- Run with `--format json` and validate JSON structure matches `AnalysisReport` schema
