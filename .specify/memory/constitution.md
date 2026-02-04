# Agent-Auditor-SDK Constitution

> **Version**: 1.0.0  
> **Created**: 2026-02-03  
> **Status**: Active

---

## Mission

Provide a quota-aware AI scheduling SDK that **guarantees human requests never fail** due to background AI task consumption, while maximizing utilization of available API quota.

---

## Core Principles

### I. Human Priority is Non-Negotiable

Human interactive requests MUST always succeed when quota exists. There are no exceptions. Background tasks are optimizations; human blocking is failure.

### II. Security-First API Key Handling

1. API keys MUST only be read from environment variables
2. API keys MUST NEVER be logged, serialized, or exposed in error messages
3. API keys MUST be sanitized from all stack traces and debug output
4. No hardcoded keys, no config files containing secrets

### III. Async-First Architecture

1. All I/O operations MUST be async (no blocking calls)
2. Use `asyncio` and `httpx` for network operations
3. No synchronous API calls in production code paths

### IV. ToS Compliance

1. MUST respect all Gemini API rate limits (RPM, TPM, RPD)
2. MUST implement exponential backoff on 429 errors
3. MUST NOT retry aggressively (max 5 retries with increasing delays)
4. Single-user key usage only (Brandon Fox)

### V. Test-Driven Development

1. All behavior specifications MUST have acceptance tests
2. All public API methods MUST have unit tests
3. Tests MUST be written BEFORE implementation
4. No code merges without passing test suite

### VI. SOLID Principles

1. **Single Responsibility**: Each class/module has one reason to change
2. **Open/Closed**: Open for extension, closed for modification
3. **Liskov Substitution**: Subtypes must be substitutable for base types
4. **Interface Segregation**: Many specific interfaces over one general
5. **Dependency Inversion**: Depend on abstractions, not concretions

### VII. 12-Factor App Compliance

1. **Codebase**: One codebase, many deploys
2. **Dependencies**: Explicitly declare (pyproject.toml)
3. **Config**: Store in environment variables (GEMINI_API_KEY)
4. **Backing Services**: Treat as attached resources
5. **Build/Release/Run**: Strictly separate stages
6. **Processes**: Stateless processes (persist to SQLite/external)
7. **Port Binding**: Export services via port binding
8. **Concurrency**: Scale out via process model
9. **Disposability**: Fast startup, graceful shutdown
10. **Dev/Prod Parity**: Keep environments similar
11. **Logs**: Treat as event streams (stdout)
12. **Admin Processes**: Run as one-off processes

### VIII. DRY (Don't Repeat Yourself)

1. Extract common logic into shared utilities
2. Use inheritance/composition for shared behavior
3. Single source of truth for constants and config
4. Avoid copy-paste; refactor to reuse

### IX. Predictable Scheduling

1. Background tasks MUST be cancellable without data loss
2. Task queue MUST survive process restarts
3. Quota predictions MUST be conservative (err on the side of underutilization)

---

## Quality Gates

Before any code is shipped, the following MUST pass:

| Gate | Requirement |
|------|-------------|
| **Unit Tests** | 100% pass, >80% coverage |
| **Type Checking** | `mypy --strict` passes |
| **Linting** | `ruff check` passes |
| **Security Scan** | No hardcoded secrets |
| **BDD Tests** | All acceptance scenarios pass |

---

## Constraints

### Must Have
- Python 3.11+
- Pydantic for data validation
- httpx for async HTTP
- pytest + pytest-asyncio for testing

### Must NOT Have
- Synchronous `requests` library
- Hardcoded API keys
- Blocking I/O in async contexts
- Uncaught exceptions exposing sensitive data

---

## Development Workflow

```
1. Spec (SDD)     → Define WHAT in specs/
2. Behavior (BDD) → Given/When/Then acceptance tests
3. Unit (TDD)     → Failing unit tests FIRST
4. Implement      → Write minimal code to pass tests
5. Refactor       → Clean up while tests stay green
```

---

## Git & Commit Practices

### X. Atomic Commits

1. Each commit MUST be atomic and self-contained
2. Each commit MUST leave the codebase in a working state
3. Commit after each logical unit of work (single feature/fix)
4. Commit message format: `type(scope): description`
   - Types: feat, fix, test, docs, refactor, chore

### XI. Branch Strategy

1. Feature branches: `feat/001-feature-name` from `main`
2. Stacked PRs: No PR larger than 30 minutes of review
3. PR naming: `[001] Feature Name - Part N/M`
4. Each PR should be independently mergeable when possible

### XII. Rollback Safety

1. All changes MUST be reversible via `git revert`
2. Database migrations MUST have rollback scripts
3. Feature flags for risky deployments
4. No force-push to shared branches

---

*This constitution governs all development in Agent-Auditor-SDK.*
