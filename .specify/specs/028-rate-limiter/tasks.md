# Tasks: Rate Limiter Token Bucket

**Input**: specs/028-rate-limiter/ | **Prerequisites**: spec.md, plan.md

## Phase 1: Setup

- [ ] T001 Create `src/limiting/` directory

---

## Phase 2: Foundational

- [ ] T002 Define TokenBucket class
- [ ] T003 [P] Implement token refill logic

---

## Phase 3: User Story 1 - Limit Request Rate (P1) 🎯 MVP

- [ ] T004 [US1] Implement `acquire()` method
- [ ] T005 [US1] Queue requests when bucket empty
- [ ] T006 [US1] Support configurable rate/burst
- [ ] T007 [US1] Integrate with async workflow

---

## Phase 4: Polish

- [ ] T008 [P] Add metrics/monitoring
- [ ] T009 [P] Write rate limiting tests
