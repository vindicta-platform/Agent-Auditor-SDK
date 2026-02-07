# Tasks: Task Queue Persistence

**Input**: specs/027-task-queue/ | **Prerequisites**: spec.md, plan.md

## Phase 1: Setup

- [ ] T001 Create `src/persistence/` directory
- [ ] T002 [P] Create SQLite schema

---

## Phase 2: Foundational

- [ ] T003 Define TaskEntry Pydantic model
- [ ] T004 [P] Initialize SQLite connection

---

## Phase 3: User Story 1 - Persist Pending Tasks (P1) 🎯 MVP

- [ ] T005 [US1] Implement `enqueue()` method
- [ ] T006 [US1] Implement `restore()` method
- [ ] T007 [US1] Implement `complete()` method
- [ ] T008 [US1] Verify queue survives restart

---

## Phase 4: Polish

- [ ] T009 [P] Optimize restore for <100ms
- [ ] T010 [P] Write persistence tests
