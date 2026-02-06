# Agent-Auditor-SDK Constraints

> Critical rules agents MUST follow when modifying this repository.

## ⛔ Hard Constraints

1. **Single Quota Authority** - This is THE source of truth for AI quotas
2. **Async-First** - All I/O operations must be async
3. **No Direct API Calls** - All AI calls go through adapters
4. **Fail-Safe Defaults** - On error, deny execution (safe mode)

## 📊 Quota Rules

### Budget Tiers
```python
DAILY_BUDGET = {
    "debate": 100,      # Meta-Oracle debates
    "grade": 500,       # List grading
    "general": 1000,    # General AI calls
}
```

### Enforcement
- Hard limits: Cannot exceed, request rejected
- Soft limits: Warning issued, execution continues
- Emergency reserve: 10% held for critical operations

### Priority Levels
```python
PRIORITY_CRITICAL = 0   # System health
PRIORITY_HIGH = 1       # User-facing
PRIORITY_NORMAL = 2     # Background
PRIORITY_LOW = 3        # Batch jobs
```

## 🔒 Security Rules

- API keys stored in environment variables only
- No quota data in logs (PII adjacent)
- Rate limit enforcement at adapter level

## 🧪 Testing Requirements

Before merging:
- [ ] `pytest` passes
- [ ] Quota enforcement tests pass
- [ ] Adapter mocks used (no real API calls in tests)
- [ ] Persistence layer tested in isolation
