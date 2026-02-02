# Agent-Auditor-SDK

A Python SDK for building "Mechanical Auditor" agents that verify AI-generated outputs against ground-truth rules and data.

## Overview

The Agent-Auditor-SDK provides the foundational framework for creating agents that audit, validate, and enforce correctness in AI pipelines. It is a core component of the Vindicta Platform's quality assurance infrastructure.

## Features

- **Rule-Based Validation**: Verify outputs against defined rule sets
- **Citation Checking**: Ensure all claims reference valid source IDs
- **Entity Whitelisting**: Reject mentions of entities not in approved lists
- **Structured Outputs**: JSON-based audit reports with failure details
- **Quota-Aware Scheduling**: Prioritize human requests, use surplus for background audits

## Installation

Install from source using uv:

```bash
uv pip install git+https://github.com/vindicta-platform/Agent-Auditor-SDK.git
```

Or clone and install locally:

```bash
git clone https://github.com/vindicta-platform/Agent-Auditor-SDK.git
cd Agent-Auditor-SDK
uv pip install -e .
```

## Quick Start

```python
from agent_auditor import RuleSage, AuditResult

auditor = RuleSage(
    rules_path="./rules.json",
    entities_whitelist=["Unit1", "Unit2"]
)

result: AuditResult = auditor.validate(agent_output)

if not result.valid:
    print(result.failures)
    print(result.correction_prompt)
```

## Use Cases

- **Meta-Oracle Integration**: Validate debate round outputs
- **WARScribe Compliance**: Ensure game data follows notation rules
- **LLM Pipeline QA**: Add verification checkpoints in AI workflows

## Repository Structure

```
Agent-Auditor-SDK/
├── src/                 # SDK source code
├── tests/               # Unit and integration tests
├── docs/                # Documentation and ADRs
├── specs/               # Feature specifications
└── examples/            # Usage examples
```

## Related Repositories

| Repository | Relationship |
|------------|-------------|
| [platform-core](https://github.com/vindicta-platform/platform-core) | Parent platform |
| [WARScribe-Parser](https://github.com/vindicta-platform/WARScribe-Parser) | Data validation target |

## License

MIT License - See [LICENSE](./LICENSE) for details.

## Contributing

See [docs/SETUP.md](./docs/SETUP.md) for development setup instructions.
