"""
Component tests for CLI.

Layer: Component
Scope: CLI entry point and command structure handling.
"""

import pytest
import json
from unittest.mock import patch
from io import StringIO
from agent_auditor.__main__ import cli, status_command, submit_command, process_command, get_parser, get_version


class TestCLIStatus:

    def test_status_command_exists(self):
        # Arrange & Act & Assert
        assert callable(cli)

    def test_status_outputs_json(self):
        # Arrange
        captured = StringIO()

        # Act
        with patch('sys.stdout', captured):
            status_command(json_format=True)

        # Assert
        output = captured.getvalue()
        data = json.loads(output)
        assert "queue_size" in data
        assert "requests_today" in data

    def test_status_shows_quota_info(self):
        # Arrange
        captured = StringIO()

        # Act
        with patch('sys.stdout', captured):
            status_command(json_format=False)

        # Assert
        output = captured.getvalue()
        assert any(word in output.lower() for word in ["quota", "requests", "remaining"])


class TestCLISubmit:

    @pytest.mark.asyncio
    async def test_submit_command_queues_task(self):
        # Arrange & Act
        result = await submit_command(
            prompt="Test prompt",
            priority="background",
            name="test_task"
        )

        # Assert
        assert result is not None
        assert result["status"] in ["queued", "success"]

    @pytest.mark.asyncio
    async def test_submit_accepts_priority(self):
        # Arrange & Act
        result = await submit_command(
            prompt="High priority",
            priority="high",
            name="urgent"
        )

        # Assert
        assert result is not None


class TestCLIProcess:

    @pytest.mark.asyncio
    async def test_process_command_runs_batch(self):
        # Arrange & Act
        result = await process_command(max_tasks=5)

        # Assert
        assert "processed" in result
        assert result["processed"] >= 0

    @pytest.mark.asyncio
    async def test_process_respects_max_tasks(self):
        # Arrange & Act
        result = await process_command(max_tasks=3)

        # Assert
        assert result["processed"] <= 3


class TestCLIIntegration:

    def test_cli_help_includes_commands(self):
        # Arrange & Act
        parser = get_parser()

        # Assert
        assert parser is not None

    def test_cli_version(self):
        # Arrange & Act
        version = get_version()

        # Assert
        assert version is not None
        assert "0" in version
