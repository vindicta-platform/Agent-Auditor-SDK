"""
Behave environment hooks for Agent-Auditor-SDK.
Handles asyncio loops and database isolation per scenario.
"""

import asyncio
import os
import tempfile
import shutil
from behave import use_fixture  # Will allow custom fixtures if needed

# =============================================================================
# Hooks
# =============================================================================

def before_all(context):
    """Global setup."""
    # Ensure strict separation of environments
    context.config.setup_logging()

def before_feature(context, feature):
    """Feature-level setup."""
    pass

def before_scenario(context, scenario):
    """
    Scenario setup:
    1. Create a fresh async loop.
    2. Create a unique temporary database path for isolation.
    """
    # 1. Async Loop Management
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)

    # 2. Database Isolation (Strategy: Unique Temp File per Scenario)
    # We don't create the file, just the path. The SDK code should create the DB.
    context.temp_dir = tempfile.mkdtemp()
    context.db_path = os.path.join(context.temp_dir, f"test_{scenario.name.replace(' ', '_')}.db")

    # Inject into environment for SDK to find (if using env vars)
    os.environ["AGENT_AUDITOR_DB_PATH"] = context.db_path

    # 3. Live vs Mock Mode
    if "live" in scenario.effective_tags:
        if not os.environ.get("GEMINI_API_KEY"):
            scenario.skip("Skipping @live scenario: GEMINI_API_KEY not found.")
    else:
        # Enforce Mock Mode
        os.environ["GEMINI_API_KEY"] = "mock-key-123"

def after_scenario(context, scenario):
    """
    Scenario teardown:
    1. Close loop.
    2. Cleanup temp DB.
    """
    # 1. Cleanup Async
    if hasattr(context, "loop"):
        context.loop.close()
        asyncio.set_event_loop(None)

    # 2. Cleanup Filesystem
    if hasattr(context, "temp_dir"):
        shutil.rmtree(context.temp_dir, ignore_errors=True)

    # 3. Cleanup Env
    if "AGENT_AUDITOR_DB_PATH" in os.environ:
        del os.environ["AGENT_AUDITOR_DB_PATH"]

def after_all(context):
    """Global teardown."""
    pass
