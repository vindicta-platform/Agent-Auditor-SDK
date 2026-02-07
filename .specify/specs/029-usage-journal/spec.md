# Feature Specification: Usage Journal Export

**Feature Branch**: `029-usage-journal`
**Created**: 2026-02-06
**Status**: Draft
**Target**: Week 4 | **Repository**: Agent-Auditor-SDK

## User Scenarios & Testing

### User Story 1 - Export Usage Data (Priority: P1)

SDK exports usage journal for analysis/billing.

**Acceptance Scenarios**:
1. **Given** usage history, **When** export called, **Then** CSV/JSON generated
2. **Given** date range, **When** filtered export, **Then** only range included

---

## Requirements

### Functional Requirements
- **FR-001**: SDK MUST export to CSV and JSON
- **FR-002**: SDK MUST support date range filtering
- **FR-003**: SDK MUST include all quota-affecting actions

### Key Entities
- **UsageEntry**: timestamp, action, cost, userId
- **UsageJournal**: entries[], exportFormat

## Success Criteria
- **SC-001**: Export 1000 entries in <2s
- **SC-002**: 100% data accuracy
