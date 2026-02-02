# Getting Started

## Installation

```bash
uv pip install git+https://github.com/vindicta-platform/Agent-Auditor-SDK.git
```

## Basic Usage

```python
from agent_auditor import Inspector, Policy

# Create inspector with policy
policy = Policy.from_constitution("constitution.md")
inspector = Inspector(policy)

# Verify agent output
result = inspector.verify(agent_output)
```
