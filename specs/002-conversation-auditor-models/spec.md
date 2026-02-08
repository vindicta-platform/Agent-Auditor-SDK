# Feature Specification: Conversation Auditor Models

**Feature Branch**: `002-conversation-auditor-models`
**Created**: 2026-02-07
**Status**: Draft
**Input**: Build a retrospective conversation analysis system within the Agent-Auditor-SDK that performs per-prompt analysis of AI conversations to identify inflection points where model selection could be optimized. The system defines a Model Decision Matrix ranking models across capability dimensions, strict Reward Functions for scoring model choices (quality, efficiency, context continuity), and a Context Switching Cost Model to quantify the penalty of mid-conversation model changes. The output is a structured Analysis Report with an optimal switching schedule and improvement metrics.

## Problem Statement

The Agent-Auditor-SDK manages AI API quotas and task scheduling, but has no mechanism to evaluate *whether the right model was used for each prompt*. When conversations span multiple task types—from simple chat to complex code generation to deep reasoning—using a single model for all turns leads to either quality waste (over-powered models on trivial tasks) or quality loss (under-powered models on complex tasks).

The core challenge: **How do we retrospectively analyze conversations, classify each prompt by task archetype, score model fitness against those archetypes, and produce actionable recommendations for optimal model switching—while accounting for the real costs of mid-conversation context transfer?**

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrospective Conversation Analysis (Priority: P0)

As an **AI Operations Engineer**, I want to analyze completed conversations to identify where a different model would have produced better results, so that I can optimize model routing policies for future conversations.

**Why this priority**: This is the core value proposition—without analysis, there is no optimization insight.

**Acceptance Scenarios**:
1. **Given** a completed conversation transcript (JSON), **When** I run the analyzer, **Then** I receive a structured report identifying every inflection point where the model selection was suboptimal.
2. **Given** a conversation with mixed task types (chat, code generation, reasoning), **When** the analyzer processes it, **Then** each user prompt is classified into a task archetype with a confidence score.
3. **Given** a conversation where all turns used the same model, **When** the analyzer evaluates it, **Then** the report shows a potential improvement percentage based on counterfactual optimal model selections.

---

### User Story 2 - Model Decision Matrix (Priority: P0)

As an **AI Operations Engineer**, I want models scored across multiple capability dimensions (quality, speed, cost, tool use, code), so that I can objectively compare model fitness for each task archetype.

**Why this priority**: The decision matrix is the foundation for all scoring and recommendation logic.

**Acceptance Scenarios**:
1. **Given** a model decision matrix with registered models, **When** I query a model's capability for a specific archetype, **Then** I receive a normalized score (0.0–1.0) weighted by archetype-specific dimension importance.
2. **Given** two models with different capability profiles, **When** I compare them for a CODE_GEN archetype, **Then** the model with higher code and quality scores ranks higher.
3. **Given** a custom matrix configuration, **When** I inject it into the engine, **Then** all scoring uses the custom matrix instead of defaults.

---

### User Story 3 - Reward-Based Model Scoring (Priority: P0)

As an **AI Operations Engineer**, I want each model selection scored using a composite reward function balancing quality, efficiency, and context continuity, so that recommendations account for all operational trade-offs.

**Why this priority**: A single-dimensional score (e.g., quality only) would ignore the cost and disruption of model switching. The composite reward captures the full picture.

**Acceptance Scenarios**:
1. **Given** a model selection at a conversation turn, **When** the reward evaluator scores it, **Then** the total reward is a weighted combination of quality reward (R1), efficiency reward (R2), and context reward (R3).
2. **Given** a model switch from one provider to another mid-conversation, **When** the context reward is calculated, **Then** it is penalized proportionally to the estimated context loss.
3. **Given** a reward configuration with custom weights, **When** I override the default weights, **Then** the composite score shifts to prioritize the adjusted dimensions.

---

### User Story 4 - Context Switching Cost Quantification (Priority: P1)

As an **AI Operations Engineer**, I want mid-conversation model switches penalized based on provider mismatch, tier difference, and tool state complexity, so that recommendations only suggest switches when the quality gain exceeds the switching cost.

**Why this priority**: Switching models mid-conversation has real costs—context loss, latency, format translation—that must be weighed against potential quality gains.

**Acceptance Scenarios**:
1. **Given** a switch between two models from the same provider (e.g., Gemini Pro → Gemini Flash), **When** the cost model calculates the loss ratio, **Then** the penalty is minimal (base tier penalty only).
2. **Given** a switch between two models from different providers (e.g., Gemini → Claude), **When** the cost model calculates the loss ratio, **Then** it includes an additional cross-provider penalty for format translation overhead.
3. **Given** a switch when the conversation has active tool state, **When** the cost model calculates the loss ratio, **Then** it includes an additional penalty for tool state re-initialization.
4. **Given** any transition, **When** the cost model calculates the loss ratio, **Then** the result is capped at a maximum threshold to prevent excessive penalties from blocking all switches.

---

### User Story 5 - Archetype Classification (Priority: P1)

As an **AI Operations Engineer**, I want each user prompt automatically classified into a task archetype (Planning, Code Generation, Code Editing, Reasoning, Search, Review, Chat, Multi-Step), so that the correct model capability profile is applied to each turn.

**Why this priority**: Classification accuracy directly impacts the quality of analysis recommendations.

**Acceptance Scenarios**:
1. **Given** a prompt like "Write a Python function to sort a list", **When** the classifier processes it, **Then** it returns CODE_GEN as the archetype.
2. **Given** a prompt like "Analyze this complex logical paradox", **When** the classifier processes it, **Then** it returns REASONING as the archetype.
3. **Given** a prompt that doesn't match any pattern strongly, **When** the classifier processes it, **Then** it returns UNKNOWN with a low confidence score and logs a classification miss for future improvement.
4. **Given** a low-confidence classification, **When** logged to the miss journal, **Then** the entry captures the prompt snippet, predicted archetype, and confidence for labeling review.

---

### User Story 6 - CLI Analysis Output (Priority: P2)

As an **AI Operations Engineer**, I want to analyze conversations from the command line with text or JSON output, so that I can integrate analysis into scripts and automation pipelines.

**Why this priority**: A CLI interface enables batch analysis and integration with existing operational tooling.

**Acceptance Scenarios**:
1. **Given** a conversation transcript JSON file, **When** I run `agent_auditor analyze --file transcript.json`, **Then** I see a human-readable summary including total turns, potential improvement percentage, and the optimal switching schedule.
2. **Given** the same file, **When** I run the command with `--format json`, **Then** I receive the full structured analysis report as JSON.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Task Archetype Classification)**: The system MUST classify each user prompt into one of the defined task archetypes (PLANNING, CODE_GEN, CODE_EDIT, REASONING, SEARCH, REVIEW, CHAT, MULTI_STEP, UNKNOWN) using heuristic pattern matching.

- **FR-002 (Classification Confidence)**: Each classification MUST produce a confidence score (0.0–1.0) representing the relative strength of the top match. Low-confidence classifications MUST be logged to a miss journal for review.

- **FR-003 (Model Decision Matrix)**: The system MUST maintain a decision matrix mapping registered models to normalized capability scores across dimensions: quality, speed, cost, context window, tool use, and code.

- **FR-004 (Archetype-Weighted Scoring)**: Each task archetype MUST have dimension weights that determine relative importance. Model scoring for a given archetype MUST apply these weights to produce a normalized composite score.

- **FR-005 (Composite Reward Function)**: Model selection scoring MUST use a composite reward function: `R_total = w_quality × R1 + w_efficiency × R2 + w_context × R3`, where:
  - R1 (Quality): Model capability score weighted by archetype
  - R2 (Efficiency): Weighted combination of speed and cost scores
  - R3 (Context): Penalty for mid-conversation model switching

- **FR-006 (Context Switching Cost)**: The system MUST quantify context loss as a ratio (0.0–1.0, capped at 0.4) incorporating:
  - Base tier penalty (e.g., Pro → Flash)
  - Cross-provider penalty (e.g., Gemini → Claude)
  - Tool state re-initialization penalty (when active tool state exists)

- **FR-007 (Retrospective Analysis Pipeline)**: The system MUST process a list of conversation turns and for each user prompt:
  1. Classify the archetype
  2. Score the model actually used
  3. Score all available models counterfactually
  4. Identify the optimal model and calculate the reward delta

- **FR-008 (Analysis Report)**: The system MUST produce a structured report containing: conversation ID, total turns, inflection points with per-turn metadata, actual vs. optimal total reward, potential improvement percentage, estimated cost savings, and an optimal switching schedule.

- **FR-009 (Switching Schedule)**: The analysis report MUST include a recommended switching schedule listing turns where a model switch would improve rewards, filtered by a significance threshold (delta > 0.02).

- **FR-010 (Configurable Matrix)**: The model decision matrix MUST support injection of custom model definitions and archetype weights, enabling adaptation to different model landscapes without code changes.

- **FR-011 (CLI Integration)**: The system MUST expose an `analyze` subcommand in the `agent_auditor` CLI accepting a transcript JSON file, optional conversation ID, and output format (text/JSON).

- **FR-012 (Usage Journal Integration)**: The usage journal MUST support querying entries by conversation ID to enable correlation of actual usage data with analysis results.

### Key Entities

- **Task Archetype**: An enumerated classification of user prompt intent (PLANNING, CODE_GEN, CODE_EDIT, REASONING, SEARCH, REVIEW, CHAT, MULTI_STEP, UNKNOWN).

- **Conversation Turn**: A single message in a conversation, capturing role (user/assistant), content, model used, timestamp, and metadata.

- **Model Capability Score**: A normalized multi-dimensional profile for a single AI model (quality, speed, cost, context window, tool use, code).

- **Inflection Point**: A user prompt annotated with its archetype, the model actually used, the optimal model, and the reward delta between them.

- **Model Recommendation**: A specific turn-level suggestion to switch models, with confidence, reasoning, and expected reward improvement.

- **Analysis Report**: The complete output of retrospective analysis, aggregating inflection points, rewards, improvement metrics, and the switching schedule.

- **Classification Miss**: A logged event when archetype classification confidence falls below threshold, capturing the prompt snippet and prediction for improvement labeling.

- **Reward Config**: A tunable configuration controlling the weights of quality, efficiency, and context components in the composite reward function.

### Assumptions

- **Model Data is Seeded**: Default model capability scores are pre-configured for Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash, Claude 4 Opus, Claude 4 Sonnet, and a generic OSS model. Users can override via configuration injection.
- **Heuristic Classification**: The initial classifier uses regex-based heuristics, not ML. Accuracy is expected to be moderate (~70-80%) for well-formed prompts, with the miss journal supporting iterative improvement.
- **Retrospective Only**: This feature analyzes completed conversations. Real-time routing is out of scope for this specification.
- **Cost Savings Estimate**: The savings estimate is a simplified heuristic index (delta × 0.1), not a precise dollar-value calculation. Pricing integration is deferred.
- **Context Loss Model**: Context loss ratios are approximated via provider/tier heuristics, not measured empirically. The cap at 40% prevents pathological penalty accumulation.

### Non-Functional Requirements

- **NFR-001 (Analysis Speed)**: Analysis of a 100-turn conversation completes in under 500 milliseconds (excluding I/O).
- **NFR-002 (Determinism)**: Given the same input transcript and configuration, the analyzer produces identical output.
- **NFR-003 (Extensibility)**: New models can be added to the decision matrix without modifying analysis logic—only configuration data changes.
- **NFR-004 (Testability)**: All reward functions, classifiers, and cost models are independently testable with no external dependencies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 6-turn mixed-task conversation (chat → code generation → reasoning) produces an analysis report identifying at least 1 inflection point where a model switch improves the reward score.
- **SC-002**: The classifier correctly identifies CODE_GEN, REASONING, and CHAT archetypes from representative prompts with confidence ≥ 0.5.
- **SC-003**: Cross-provider model switches (e.g., Gemini → Claude) produce measurably higher context loss penalties than same-provider switches.
- **SC-004**: Custom reward weights (e.g., 80% quality / 10% efficiency / 10% context) shift optimal model recommendations toward higher-quality models for reasoning tasks.
- **SC-005**: The CLI `analyze` command produces both human-readable and machine-parseable (JSON) output from a transcript file.
- **SC-006**: The potential improvement percentage for a conversation using only Flash models on reasoning-heavy prompts is greater than 0%.

## Out of Scope

- Real-time model routing or automatic model switching during live conversations
- ML-based or LLM-based archetype classification (heuristic only for v1)
- Precise dollar-cost calculations tied to provider pricing APIs
- Empirical context loss measurement (e.g., via probe queries)
- Multi-language prompt classification
- Integration with external observability platforms (e.g., LangSmith, Weights & Biases)

## Dependencies

- Existing Agent-Auditor-SDK core models (`AITask`, `RequestPriority`, `TaskResult`, `UsageEntry`)
- Existing `UsageJournal` persistence layer (conversation-aware querying)
- Pydantic v2 for data modeling and validation
- Python 3.11+ standard library
