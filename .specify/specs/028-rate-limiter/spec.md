# Feature Specification: Rate Limiter Token Bucket

**Feature Branch**: `028-rate-limiter`
**Created**: 2026-02-06
**Status**: Draft
**Target**: Week 2 | **Repository**: Agent-Auditor-SDK

## User Scenarios & Testing

### User Story 1 - Limit Request Rate (Priority: P1)

SDK enforces rate limits using token bucket algorithm.

**Acceptance Scenarios**:
1. **Given** tokens available, **When** request made, **Then** allowed
2. **Given** no tokens, **When** request made, **Then** queued until token

---

## Requirements

### Functional Requirements
- **FR-001**: SDK MUST implement token bucket algorithm
- **FR-002**: SDK MUST support configurable rate/burst
- **FR-003**: SDK MUST queue requests when bucket empty

### Key Entities
- **TokenBucket**: tokens, rate, burst, lastRefill

## Success Criteria
- **SC-001**: Rate limiting accurate to ±5%
- **SC-002**: Zero dropped requests
