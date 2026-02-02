# Setup Guide

## Prerequisites

- Python 3.10+
- uv or pip

## Development Setup

```bash
# Clone the repository
git clone https://github.com/vindicta-platform/Agent-Auditor-SDK.git
cd Agent-Auditor-SDK

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

## Running Tests

```powershell
pytest tests/ -v
```

## Code Quality

```powershell
# Linting
ruff check .

# Formatting
ruff format .
```

## Contributing

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass
4. Submit a pull request
