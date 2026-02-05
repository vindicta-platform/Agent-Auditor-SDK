# 2. Use Behave for BDD Testing

Date: 2026-02-05

## Status

Accepted

## Context

The Agent-Auditor-SDK requires a robust acceptance testing framework to ensure that complex features like Quota-Aware Scheduling and Human Priority Guarantees meet Product Owner requirements. 

Currently, acceptance tests are written in pure Python (`test_acceptance.py`), which are hard for non-technical stakeholders to read and verify. We need a "Black Box" testing layer that:
1. Validates the "WHAT" (Business Behavior) separately from the "HOW" (Implementation).
2. Uses natural language (Gherkin) for collaboration with Product Owners.
3. Supports a 6-layer testing strategy (Unit, Component, Functional, Integration, Live, Performance).

We considered:
- **Pytest-BDD**: Good integration with pytest, but less strict separation of concerns.
- **Behave**: Strict Gherkin enforcement, clean separation of steps, and widely understood by non-technical stakeholders.

## Decision

We will use **Behave** as the standard tool for all Black Box acceptance tests (`features/`).

1. **Strict Separation**: `features/` will contain Gherkin `.feature` files and `steps/` definitions. `tests/` will remain exclusive to Pytest white-box tests.
2. **Layered Structure**: Behave features will be organized into `functional` (business rules), `integration` (workflows), and `live` (real API) layers.
3. **Async Support**: We will implement `asyncio` loop management in `features/environment.py` to support the SDK's async nature.

## Consequences

**Positive**:
- **Readability**: Features are readable by Product Owners.
- **Strict Boundaries**: Prevents implementation details from leaking into acceptance criteria.
- **Reusability**: "Given" steps (e.g., "Given a valid API key") can be reused across Functional, Integration, and Live layers.

**Negative**:
- **Complexity**: Requires maintaining a separate runner (`behave`) alongside `pytest`.
- **Async Handling**: Behave is synchronous by default; we must explicitly manage event loops for async steps.
- **Migration Cost**: Existing pure-Python acceptance tests must be rewritten in Gherkin.
