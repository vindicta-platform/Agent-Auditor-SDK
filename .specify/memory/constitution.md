# Agent-Auditor-SDK Constitution

**Version**: 1.0.0 | **Ratified**: 2026-02-01

## Purpose

This constitution governs agentic development within the Agent-Auditor-SDK repository.

---

## Core Principles

### I. Mechanical Fidelity
All validation logic MUST produce deterministic, reproducible results. Auditor agents MUST NOT guess or infer—they verify against ground truth only.

### II. Spec-Driven Development
All features require a specification in `specs/` before implementation. BDD scenarios define acceptance criteria.

### III. Citation Integrity
When validating claims, the SDK MUST require explicit citations to rule IDs or source references. Uncited claims are invalid by default.

### IV. Quota Awareness
Background processing MUST respect human priority. The 50% reserve rule ensures user requests are never blocked.

### V. Structured Outputs
All audit results MUST be JSON-serializable with:
- `valid`: boolean
- `failures`: list of specific issues
- `correction_prompt`: actionable guidance

### VI. Test Coverage
Minimum 80% line coverage. Audit logic paths require 95%+ coverage.

---

## Platform Integration

This SDK is a standalone package that integrates with:
- `platform-core`: For economy/quota management
- `WARScribe-Parser`: As a validation target
- `Meta-Oracle`: For debate audit pipelines

---

## Governance

This constitution is subordinate to the main platform-core constitution. Amendments require platform maintainer approval.
