# Research: Conversation Auditor Models

**Feature**: 002-conversation-auditor-models
**Created**: 2026-02-07

## R1: Prompt Classification Approach

**Decision**: Heuristic regex-based pattern matching
**Rationale**: The Agent-Auditor-SDK operates under the Economic Prime Directive (GCP Free Tier). Using an LLM for classification would consume quota that should be reserved for user-facing tasks. Regex heuristics are deterministic, zero-cost, and fast. The miss journal provides a feedback loop for iterative accuracy improvement without runtime cost.
**Alternatives Considered**:
- LLM-based classification: High accuracy but costs API quota per analysis run
- Lightweight ML (scikit-learn): Moderate accuracy but adds model artifact management and scikit-learn dependency
- Embedding similarity: Good accuracy but requires embedding model calls (quota cost)

## R2: Reward Function Structure

**Decision**: Three-component composite: `R_total = w1·R_quality + w2·R_efficiency + w3·R_context`
**Rationale**: Multi-objective optimization is standard in decision systems. The three components capture the key trade-offs: response quality (capability match), operational efficiency (speed × cost), and transition disruption (context continuity). Configurable weights allow adaptation to different operational priorities (e.g., quality-first for code generation, cost-first for chat).
**Alternatives Considered**:
- Single quality score: Simple but ignores cost and disruption trade-offs
- Pareto frontier: Mathematically rigorous but introduces UI complexity for presenting non-dominated solutions
- Bayesian optimization: Powerful but requires historical outcome data not yet available

## R3: Context Loss Quantification

**Decision**: Provider/tier-based heuristic with capped loss ratio (max 0.4)
**Rationale**: Empirical context loss measurement would require sending probe queries to both models (consuming quota). The heuristic captures the three primary drivers: (1) tier switching cost (minor format differences), (2) provider switching cost (major format/capability translation), (3) tool state re-initialization (loss of accumulated tool call context). The 0.4 cap prevents pathological penalties from blocking all switches.
**Alternatives Considered**:
- Empirical probing: Most accurate but costs quota (2+ API calls per switch evaluation)
- Fixed penalty: Simple but doesn't differentiate between minor (same-provider) and major (cross-provider) switches
- No penalty: Ignores real switching costs, leads to recommendations with excessive switching

## R4: Model Decision Matrix Structure

**Decision**: Normalized capability dimensions (0.0–1.0) with archetype-specific dimension weights
**Rationale**: A matrix structure allows objective comparison across models regardless of specific benchmarks. Normalized scores enable consistent comparison. Archetype weights encode domain knowledge about what matters most for each task type (e.g., code quality matters more for CODE_GEN than CHAT).
**Alternatives Considered**:
- Benchmark-based scoring: Would tie matrix to specific benchmarks that change frequently
- Elo-based ranking: Simpler but loses dimensional information (a model could be fast but low quality)
- Binary capability flags: Too coarse for nuanced optimization

## R5: Integration Strategy

**Decision**: Additive integration — new `analysis/` subpackage, no modifications to existing function signatures
**Rationale**: Constitution mandates Zero-Issue Stability. Adding a new subpackage with its own exports avoids any risk of breaking existing tests or consumers. The only modification to existing code is adding an optional `conversation_id: Optional[str] = None` field to `UsageEntry` (backward-compatible default) and a new `query_by_conversation()` method to `UsageJournal`.
**Alternatives Considered**:
- Inline integration into existing models.py: Simpler but mixes concerns, risks breaking existing tests
- Separate package: Over-isolated, prevents natural access to existing models and journal
