"""
SQLite journal schema for Agent-Auditor-SDK.

Defines the database schema for usage journaling per Issue #7.
"""

SCHEMA_SQL = """
-- Usage journal for tracking API calls
CREATE TABLE IF NOT EXISTS usage_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    agent_id TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    latency_ms INTEGER,
    success INTEGER NOT NULL DEFAULT 1,
    error_type TEXT
);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_journal(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_agent ON usage_journal(agent_id);

-- Quota snapshots for prediction
CREATE TABLE IF NOT EXISTS quota_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time TEXT NOT NULL DEFAULT (datetime('now')),
    quota_limit INTEGER NOT NULL,
    quota_used INTEGER NOT NULL,
    quota_remaining INTEGER GENERATED ALWAYS AS (quota_limit - quota_used) STORED
);

-- Data retention: entries older than 30 days
CREATE TRIGGER IF NOT EXISTS cleanup_old_entries
AFTER INSERT ON usage_journal
BEGIN
    DELETE FROM usage_journal
    WHERE timestamp < datetime('now', '-30 days');
END;
"""
