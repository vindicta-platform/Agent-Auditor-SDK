# Feature Specification: Quota-Aware AI Scheduling

**Feature Branch**: `001-quota-aware-scheduling`
**Created**: 2026-02-01
**Status**: Draft
**Input**: User description: "Build a feature to allow for usage of my (Brandon Fox) personal access using Gemini Ultra to leverage the modeling behind vindicta. Goal is to ensure priority remains for human requests so will not use up all the available quota, but will attempt to reason how much leftover quota will be available each hour and then try and use that for local modeling and runs."

## Problem Statement

Brandon Fox has personal API access to Gemini Ultra via Google AI Studio. The Vindicta platform needs to leverage this access for background AI modeling tasks (rule arbitration, debate simulation, inference runs) WITHOUT monopolizing quota that the human user needs for interactive work.

The core challenge: **How do we maximize utilization of expensive API quota while guaranteeing human requests are never blocked?**

## Clarifications (Resolved 2026-02-01)

| Question | Answer | Implication |
|----------|--------|-------------|
| **Gemini API Tier** | Tier 2+ | Baseline: 1000+ RPM, 2M TPM, 10K+ RPD - aggressive background utilization possible |
| **Background Task Priority** | Rule-Sage Audit → Debate Simulation → Inference Batch | Validation accuracy prioritized over throughput |
| **Human Reserve** | 50% | Conservative approach - half of quota always available for interactive use |
| **Deployment Context** | Local only | Key stored in local `.env` file on Brandon's dev machine; no cloud/server deployment |
| **Authentication Method** | ADC or API Key (spike resolved) | Both work: `gcloud auth application-default login` (SSO) or `GEMINI_API_KEY` env var |

### Session 2026-02-01 (Authentication Spike)
- **Q: Can I use my personal Google SSO instead of API key?** → **A: YES.** Two valid options:
  1. **ADC (Application Default Credentials)**: Run `gcloud auth application-default login` once to cache your Google account OAuth tokens locally. The `google-generativeai` SDK auto-detects these.
  2. **API Key**: Generate from Google AI Studio, set as `GEMINI_API_KEY` or `GOOGLE_API_KEY` env var.
- **Recommendation**: Use ADC for personal SSO access (more secure, no key to manage). API key is fallback option.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Human Priority Guarantee (Priority: P1)

As **Brandon Fox (Human User)**, I want my interactive requests to ALWAYS succeed, so that I am never blocked by background AI tasks consuming my personal quota.

**Why this priority**: Human experience is non-negotiable. Background tasks are optimizations; human blocking is failure.

**Acceptance Scenarios**:
1. **Given** the quota is 90% consumed by background tasks, **When** I submit an interactive request, **Then** it succeeds immediately.
2. **Given** background tasks are queued, **When** a human request arrives, **Then** background tasks pause until the human request completes.
3. **Given** quota is exhausted, **When** I submit a human request, **Then** I receive a clear message about reset time, NOT a silent failure.

---

### User Story 2 - Predictive Quota Budgeting (Priority: P1)

As the **Arbiter Scheduler**, I want to predict how much quota headroom remains each hour based on usage patterns, so that I can safely allocate leftover capacity to background AI tasks.

**Why this priority**: Without prediction, we either waste quota (underutilization) or risk blocking humans (overutilization).

**Acceptance Scenarios**:
1. **Given** historical usage data for the past 7 days, **When** the scheduler evaluates capacity, **Then** it calculates a "safe budget" for the current hour.
2. **Given** the predicted budget is 50 requests/hour, **When** 30 are consumed by background tasks, **Then** background processing throttles.
3. **Given** usage patterns change (e.g., weekend vs weekday), **When** the scheduler runs, **Then** predictions adapt within 24 hours.

---

### User Story 3 - Background Task Execution (Priority: P2)

As the **Meta-Oracle Pipeline**, I want to run debate simulations, rule arbitration, and inference batches using surplus quota, so that the platform continuously improves without manual intervention.

**Why this priority**: Background AI work drives Vindicta's intelligence; it must happen, just not at the cost of human UX.

**Acceptance Scenarios**:
1. **Given** surplus quota exists, **When** the scheduler runs, **Then** queued background tasks execute in priority order.
2. **Given** a batch of 100 debate simulations, **When** surplus quota is 40 requests, **Then** only 40 simulations run this hour; the rest remain queued.
3. **Given** tasks have different priorities (e.g., critical rule-sage audit vs exploratory debate), **When** scheduling, **Then** higher-priority tasks execute first.

---

### User Story 4 - Quota Visibility Dashboard (Priority: P3)

As **Brandon Fox**, I want to see real-time quota status and background task activity, so that I understand how my API budget is being utilized.

**Why this priority**: Transparency builds trust; users should never wonder "where did my quota go?"

**Acceptance Scenarios**:
1. **Given** the dashboard, **When** I view it, **Then** I see: current usage, hourly limit, predicted surplus, active background tasks.
2. **Given** a spike in background usage, **When** I check the dashboard, **Then** I can identify which tasks consumed quota.
3. **Given** quota exhaustion, **When** I view the dashboard, **Then** I see the reset countdown.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 (Priority Queue)**: The system MUST implement a dual-priority queue: **HUMAN** (P0, immediate) and **BACKGROUND** (P1-P3, deferrable). Human requests ALWAYS preempt background tasks.

- **FR-002 (Human Reserve)**: The system MUST reserve **50%** of available quota for human use at all times. Background tasks MUST NOT consume beyond the 50% ceiling.

- **FR-003 (Quota Predictor)**: The system MUST implement a predictive model that estimates hourly quota surplus based on:
  - Current usage within the sliding window
  - Historical usage patterns (time-of-day, day-of-week)
  - The fixed 50% human reserve buffer

- **FR-003 (Gemini API Integration)**: The system MUST integrate with Google AI Studio / Gemini API using:
  - Personal API key authentication (environment variable: `GEMINI_API_KEY` or `AISTUDIO__API_KEY`)
  - Rate limit tracking (RPM, TPM, RPD dimensions)
  - Automatic retry with exponential backoff on 429 errors

- **FR-005 (Task Scheduler)**: The system MUST schedule background AI tasks based on:
  - Predicted surplus quota (within 50% background ceiling)
  - Task priority: Rule Sage (P1) > Debate Simulation (P2) > Inference Batch (P3)
  - Task cost estimation (tokens/requests)

- **FR-005 (Graceful Degradation)**: When quota is exhausted:
  - Human requests MUST receive a clear error with reset time
  - Background tasks MUST pause and re-queue (no data loss)
  - The system MUST NOT retry aggressively (respects API etiquette)

- **FR-006 (Audit Trail)**: The system MUST log all quota consumption with:
  - Timestamp
  - Request type (human vs background)
  - Task identifier
  - Token/request cost
  - Success/failure status

- **FR-008 (Configuration)**: The system MUST support configuration via environment variables:
  - `QUOTA_HUMAN_RESERVE_PERCENT`: Default **50%**
  - `QUOTA_PREDICTION_LOOKBACK_DAYS`: Default 7
  - `QUOTA_RPM_LIMIT`: Default **1000** (Tier 2+)
  - `QUOTA_TPM_LIMIT`: Default **2000000** (Tier 2+)
  - `QUOTA_RPD_LIMIT`: Default **10000** (Tier 2+)

### Key Entities

- **QuotaPredictor**: Engine that forecasts hourly surplus based on usage history and current state. Outputs a "safe budget" for background tasks.

- **TaskQueue**: Priority-ordered queue holding pending background AI tasks. Priority order: **P1 (Rule Sage) > P2 (Debate) > P3 (Inference)**. Supports enqueue, dequeue, pause, and resume.

- **ArbiterScheduler**: Coordinator that:
  1. Checks current quota state
  2. Queries `QuotaPredictor` for surplus
  3. Dequeues tasks from `TaskQueue` up to the surplus budget
  4. Dispatches tasks to the Gemini API adapter

- **UsageJournal**: Persistent log of all API interactions for prediction training and audit.

### Assumptions

- **Gemini API Tier**: **Tier 2+** limits as baseline (1000+ RPM, 2M TPM, 10000+ RPD).
- **Single User**: This system is designed for Brandon Fox's personal API key, not multi-tenant.
- **Hourly Granularity**: Prediction and budgeting operate at hourly intervals as a reasonable tradeoff between responsiveness and stability.
- **Local Persistence**: Usage history stored locally (SQLite/JSON), not cloud-synced.

### Non-Functional Requirements

- **NFR-001 (Latency)**: Human request routing adds less than 50ms overhead.
- **NFR-002 (Reliability)**: Background task queue survives process restarts (persisted).
- **NFR-003 (Privacy)**: API keys never logged or exposed in audit trails.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Human requests succeed 100% of the time when quota exists (zero human blocking due to background tasks).
- **SC-002**: Background task throughput is within 80-95% of predicted surplus budget (efficient utilization).
- **SC-003**: Prediction accuracy within 15% of actual usage after 7 days of training data.
- **SC-004**: System correctly pauses background tasks within 1 second when quota exhausted.
- **SC-005**: Audit log captures 100% of API interactions with complete metadata.
- **SC-006**: Dashboard displays real-time quota status with less than 5-second latency.

## Out of Scope

- Multi-tenant quota management (future feature)
- Cloud-based quota sharing across devices
- Automatic tier upgrade recommendations
- Cost optimization beyond quota management (e.g., model selection)

## Dependencies

- Existing `src/vindicta/quota` package in platform-core (QuotaManager, sliding-window logic)
- Gemini API access via personal API key
- Meta-Oracle pipeline for background task generation


## Open Questions

I am not clear how `Context: FR-003 specifies using GEMINI_API_KEY or AISTUDIO__API_KEY environment variables` will use my personal API key?


