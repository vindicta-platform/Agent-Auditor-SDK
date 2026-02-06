"""
Common steps shared across different feature layers.
"""

from behave import given, then
import os
from agent_auditor import RequestPriority

@given('the system is initialized')
def step_impl(context):
    """
    Initialize the core scheduler and dependencies.
    """
    from agent_auditor import ArbiterScheduler
    from agent_auditor.persistence.sqlite import SQLiteStorage
    
    # Initialize storage using the scenario-specific DB path
    storage = SQLiteStorage(db_path=context.db_path)
    context.loop.run_until_complete(storage.initialize())
    
    context.scheduler = ArbiterScheduler(storage=storage)

@given('a valid API key is present')
def step_impl(context):
    """
    Ensure API key is set (mock or real depending on environment).
    """
    if not os.environ.get("GEMINI_API_KEY"):
        # Should have been set by environment.py, but safe fallback
        os.environ["GEMINI_API_KEY"] = "test-key"

@given('the quota is fresh')
def step_impl(context):
    """
    Reset quota usage to zero.
    """
    if hasattr(context, "scheduler"):
        context.scheduler.reset_quota()
