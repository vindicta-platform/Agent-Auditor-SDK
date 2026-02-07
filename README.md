# Agent-Auditor-SDK

Quota-aware AI scheduling for the Vindicta Platform.

## Features

- **Human Priority Guarantee** — Human requests always execute immediately
- **Predictive Quota Budgeting** — 30% reserve for human requests
- **Background Task Execution** — Retry with exponential backoff
- **Quota Visibility** — Dashboard API and CLI

## Installation

```bash
# Clone and install from source
git clone https://github.com/vindicta/Agent-Auditor-SDK.git
cd Agent-Auditor-SDK
uv sync

# Or install as editable in another project
uv add --editable ../Agent-Auditor-SDK
```

## Quick Start

### Python API

```python
import asyncio
from agent_auditor import ArbiterScheduler, AITask, RequestPriority

async def main():
    scheduler = ArbiterScheduler()

    # Human requests execute immediately
    task = AITask(
        name="user_query",
        prompt="What's the best loadout for Space Marines?",
        priority=RequestPriority.HUMAN
    )
    result = await scheduler.submit(task)
    print(result.response)

    # Check quota status
    status = scheduler.get_status()
    print(f"Requests remaining: {status['requests_remaining']}")

asyncio.run(main())
```

### CLI

```bash
# Check status
python -m agent_auditor status --json

# Submit a background task
python -m agent_auditor submit "Analyze army composition" --priority background

# Process background queue
python -m agent_auditor process --max 10
```

## Configuration

Environment variables (12-Factor compliant):

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Your Google AI Studio API key |
| `SCHEDULER_HUMAN_RESERVE_PERCENT` | `30` | % of quota reserved for humans |
| `SCHEDULER_BATCH_SIZE` | `10` | Max tasks per batch |
| `GEMINI_DEFAULT_MODEL` | `gemini-1.5-flash` | Model for API calls |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ArbiterScheduler                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   HUMAN      │  │   TaskQueue  │  │ QuotaPredict │  │
│  │   Immediate  │  │   (Heap)     │  │ (30% reserve)│  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │
│         │                 │                              │
│         ▼                 ▼                              │
│  ┌──────────────────────────────────┐                   │
│  │         GeminiAdapter             │                   │
│  │  (Rate Limit + Exponential Backoff)│                   │
│  └──────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=agent_auditor
```

## License

MIT
