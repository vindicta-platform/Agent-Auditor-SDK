# Agent Auditor SDK

**Trust but verify: Runtime compliance for AI agents.**

Agent Auditor SDK provides tools for monitoring AI agent behavior, tracking integrity violations, and enforcing compliance policies.

## Why Audit AI Agents?

- **Detect hallucinations** — Verify rule citations
- **Track context** — Record decisions for review
- **Enforce policies** — Block non-compliant outputs

## Installation

```bash
uv pip install git+https://github.com/vindicta-platform/Agent-Auditor-SDK.git
```

## Quick Example

```python
from agent_auditor import Inspector

inspector = Inspector()
result = inspector.verify(agent_output)
if not result.valid:
    print(result.violations)
```

---

MIT License
