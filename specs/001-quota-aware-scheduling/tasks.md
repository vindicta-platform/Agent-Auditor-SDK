# Task Breakdown: Quota-Aware AI Scheduling

**Spec**: `spec.md`  
**Plan**: `plan.md`  
**Created**: 2026-02-03  
**Status**: Ready for Execution

---

## Phase 1: Setup

- [x] T001 [P] Initialize project structure in `src/agent_auditor/`
- [x] T002 [P] Configure `pyproject.toml` with dependencies
- [x] T003 [P] Create `conftest.py` with shared test fixtures

---

## Phase 2: Foundation (BLOCKS all user stories)

### Models
- [x] T010 [P] Write failing tests for `RequestPriority` enum in `tests/test_models.py`
- [x] T011 [P] Write failing tests for `AITask` model in `tests/test_models.py`
- [x] T012 [P] Write failing tests for `TaskResult` model in `tests/test_models.py`
- [x] T013 Implement `models.py` to pass tests

### Security
- [x] T020 Write failing tests for `SecureKeyManager` in `tests/test_security.py`
- [x] T021 Implement `security.py` to pass tests

### Persistence
- [x] T030 Write failing tests for `SQLiteStorage` in `tests/test_persistence.py`
- [x] T031 Implement `persistence/sqlite.py` to pass tests

---

## Phase 3: User Story 1 — Human Priority Guarantee (P1)

### Queue
- [x] T100 [US1] Write failing tests for `TaskQueue.enqueue()` in `tests/test_queue.py`
- [x] T101 [US1] Write failing tests for `TaskQueue.dequeue()` priority ordering
- [x] T102 [US1] Write failing tests for `TaskQueue.peek()`
- [x] T103 [US1] Implement `queue.py` to pass tests

### Scheduler (Human Priority)
- [/] T110 [US1] Write failing tests for `ArbiterScheduler.submit()` with HUMAN priority
- [/] T111 [US1] Write failing tests for preemption (human pauses background)
- [ ] T112 [US1] Implement `scheduler.py` with human priority logic

### Gemini Adapter
- [ ] T120 [US1] Write failing tests for `GeminiAdapter.generate()` in `tests/test_adapters.py`
- [ ] T121 [US1] Write failing tests for rate limit handling (429)
- [ ] T122 [US1] Implement `adapters/gemini.py` to pass tests

### Checkpoint US1
- [ ] T199 [US1] Run acceptance tests for User Story 1, verify all pass

---

## Phase 4: User Story 2 — Predictive Quota Budgeting (P1)

### Usage Journal
- [ ] T200 [US2] Write failing tests for `UsageJournal.record_usage()` in `tests/test_quota.py`
- [ ] T201 [US2] Write failing tests for `UsageJournal.get_history()`
- [ ] T202 [US2] Implement `UsageJournal` in `quota.py`

### Quota Predictor
- [ ] T210 [US2] Write failing tests for `QuotaPredictor.get_safe_budget()`
- [ ] T211 [US2] Write failing tests for time-of-day pattern awareness
- [ ] T212 [US2] Implement `QuotaPredictor` in `quota.py`

### Checkpoint US2
- [ ] T299 [US2] Run acceptance tests for User Story 2, verify all pass

---

## Phase 5: User Story 3 — Background Task Execution (P2)

### Dead-Letter Queue
- [ ] T300 [US3] Write failing tests for `DeadLetterQueue` in `tests/test_queue.py`
- [ ] T301 [US3] Implement `DeadLetterQueue` in `queue.py`

### Task Worker
- [ ] T310 [US3] Write failing tests for `TaskWorker.process()` in `tests/test_worker.py`
- [ ] T311 [US3] Write failing tests for retry with backoff
- [ ] T312 [US3] Write failing tests for dead-letter on failure
- [ ] T313 [US3] Implement `worker.py` to pass tests

### Batch Processing
- [ ] T320 [US3] Write failing tests for `scheduler.process_batch()`
- [ ] T321 [US3] Implement batch processing in `scheduler.py`

### Checkpoint US3
- [ ] T399 [US3] Run acceptance tests for User Story 3, verify all pass

---

## Phase 6: User Story 4 — Quota Visibility Dashboard (P3)

### Python API
- [ ] T400 [US4] Write failing tests for `scheduler.get_status()` in `tests/test_scheduler.py`
- [ ] T401 [US4] Implement `get_status()` in `scheduler.py`

### CLI
- [ ] T410 [US4] Write failing tests for CLI in `tests/test_cli.py`
- [ ] T411 [US4] Implement `__main__.py` for CLI

### Checkpoint US4
- [ ] T499 [US4] Run acceptance tests for User Story 4, verify all pass

---

## Phase 7: Polish

- [ ] T900 Run full test suite, verify 100% pass
- [ ] T901 Run mypy --strict, fix any type errors
- [ ] T902 Run ruff check, fix any lint errors
- [ ] T903 Update README with usage examples
- [ ] T904 Commit and tag v0.1.0

---

## Execution Notes

- **[P]** = Can run in parallel (different files)
- **[USX]** = Which user story this belongs to
- **Tests FIRST**: Every T0XX-T9XX test task MUST fail before implementing
- **Commit after each checkpoint**
