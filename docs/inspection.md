# Inspection

## Verification Result

```python
class VerificationResult:
    valid: bool
    violations: list[Violation]
    context: dict
```

## Violation Types

| Type | Description |
|------|-------------|
| `HALLUCINATION` | Made up fact |
| `POLICY_VIOLATION` | Broke policy |
| `CONTEXT_LEAK` | Wrong context |
