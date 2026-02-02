# Feature Proposal: Agent Auditor SDK Integration

**Proposal ID**: FEAT-016  
**Author**: Unified Product Architect (Autonomous)  
**Created**: 2026-02-01  
**Status**: Draft  
**Priority**: High  

---

## Part A: Software Design Document (SDD)

### 1. Executive Summary

Create an SDK for integrating AI agent auditing capabilities into the Vindicta platform, enabling autonomous rule verification, list validation, and game state analysis with full audit trails.

### 2. System Architecture

#### 2.1 Current State
- Standalone Agent-Auditor-SDK
- No platform integration
- Manual audit processes
- No real-time validation

#### 2.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                Agent Auditor Integration                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Audit Orchestrator                    │    │
│  │   - Request routing                                     │    │
│  │   - Quota-aware scheduling                              │    │
│  │   - Result aggregation                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                  │
│      ┌───────────────────────┼───────────────────────────┐      │
│      ▼                       ▼                       ▼          │
│ ┌──────────┐          ┌──────────┐          ┌──────────┐        │
│ │Rule-Sage │          │List-Check│          │GameState │        │
│ │ (Rules)  │          │(Validate)│          │ (Live)   │        │
│ └──────────┘          └──────────┘          └──────────┘        │
│      │                       │                       │          │
│      └───────────────────────┴───────────────────────┘          │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Gemini API                            │    │
│  │   (via Quota-Manager)                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3 File Changes

```
Agent-Auditor-SDK/
├── src/
│   └── agent_auditor/
│       ├── integration/
│       │   ├── __init__.py      [NEW]
│       │   ├── platform.py      [NEW] Platform integration
│       │   ├── rule_sage.py     [NEW] Rules Q&A agent
│       │   └── list_checker.py  [NEW] Army list validator
│       ├── quota/
│       │   ├── __init__.py      [NEW]
│       │   └── scheduler.py     [NEW] Quota-aware scheduling
│       └── audit/
│           ├── __init__.py      [NEW]
│           └── trail.py         [NEW] Audit trail recording
├── tests/
│   └── test_integration.py      [NEW]
└── docs/
    └── platform-integration.md  [NEW]
```

### 3. Audit Agents

| Agent | Purpose | Priority |
|-------|---------|----------|
| Rule-Sage | Answer rules questions with citations | P0 (Human) |
| List-Checker | Validate army lists for legality | P1 (Background) |
| GameState-Auditor | Verify live game state changes | P0 (Human) |
| Meta-Analyst | Background meta data processing | P2 (Batch) |

### 4. Quota Integration

```python
class AuditScheduler:
    """Schedule audit requests respecting quota limits."""
    
    def schedule(self, request: AuditRequest) -> AuditJob:
        priority = self.classify_priority(request)
        
        if priority == Priority.HUMAN:
            return self.execute_immediately(request)
        elif priority == Priority.BACKGROUND:
            return self.queue_for_surplus(request)
        else:
            return self.queue_for_off_peak(request)
```

### 5. Audit Trail

Every AI decision is logged to Audit-Log-Pro:
- Request context
- Agent used
- Prompt/response
- Citations/references
- Confidence score
- Token usage

---

## Part B: Behavior Driven Development (BDD)

### User Stories

#### US-001: Rules Question
**As a** player mid-game  
**I want to** ask a rules question  
**So that** I get an immediate answer with citations

#### US-002: List Validation
**As a** tournament player  
**I want** my list validated before an event  
**So that** I know it's legal

#### US-003: Audit Review
**As a** TO  
**I want to** review AI decisions  
**So that** I can verify accuracy

### Acceptance Criteria

```gherkin
Feature: Agent Auditor Integration

  Scenario: Real-time rules query
    Given I am in an active game
    When I ask "Can Necron Warriors use their reanimation protocol after being wiped?"
    Then Rule-Sage should respond within 5 seconds
    And include the relevant rulebook citation
    And log the query to audit trail

  Scenario: Background list validation
    Given I submit an army list for validation
    When the quota scheduler finds surplus capacity
    Then List-Checker should analyze the list
    And report any illegal units or wargear
    And store results for retrieval

  Scenario: Quota protection
    Given quota is at 20% of limit
    When a background validation is requested
    Then it should be deferred to off-peak
    And human requests should still be served
```

---

## Implementation Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Platform Integration | 6 hours | Quota-Manager |
| Rule-Sage Agent | 8 hours | Gemini API |
| List-Checker Agent | 6 hours | WARScribe |
| Audit Trail | 4 hours | Audit-Log-Pro |
| Testing | 4 hours | None |
| **Total** | **28 hours** | |
