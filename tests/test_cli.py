from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from secrets_cli.cli import app

runner = CliRunner()


def test_help():
    """Test help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI-friendly Secrets Management CLI" in result.stdout


def test_set_command():
    """Test set command."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "set", "TEST_KEY", "test_value"],
        )
        assert result.exit_code == 0
        assert "stored securely" in result.stdout
        mock_keyring.set_password.assert_called_once()


def test_set_command_json():
    """Test set command with JSON output."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "set", "TEST_KEY", "test_value", "-f", "json"],
        )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["name"] == "TEST_KEY"


def test_get_command():
    """Test get command."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        mock_keyring.get_password.return_value = "test_value"
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "get", "TEST_KEY"],
        )
        assert result.exit_code == 0
        assert "exists" in result.stdout


def test_get_command_print():
    """Test get command with --print flag."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        mock_keyring.get_password.return_value = "test_value"
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "get", "TEST_KEY", "--print"],
        )
        assert result.exit_code == 0
        assert "TEST_KEY: test_value" in result.stdout


def test_get_nonexistent():
    """Test get command for non-existent secret."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        mock_keyring.get_password.return_value = None
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "get", "NONEXISTENT"],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_list_command_empty(tmp_path: Path):
    """Test list command with no secrets."""
    with patch("secrets_cli.storage.keyring"):
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", str(tmp_path), "list"],
        )
        assert result.exit_code == 0
        assert "No secrets stored" in result.stdout


def test_list_command_json(tmp_path: Path):
    """Test list command with JSON output."""
    with patch("secrets_cli.storage.keyring"):
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", str(tmp_path), "list", "-f", "json"],
        )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert "secrets" in output
        assert "count" in output
        assert isinstance(output["secrets"], list)


def test_delete_command():
    """Test delete command with confirmation."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        mock_keyring.get_password.return_value = "test_value"
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "delete", "TEST_KEY", "--yes"],
        )
        assert result.exit_code == 0
        assert "deleted" in result.stdout
        mock_keyring.delete_password.assert_called_once()


def test_delete_nonexistent():
    """Test delete command for non-existent secret."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        mock_keyring.get_password.return_value = None
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", ".test-secrets", "delete", "NONEXISTENT", "--yes"],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_export_bash(tmp_path: Path):
    """Test export command with bash format."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        def mock_get_password(service: str, name: str):
            return {"KEY1": "value1", "KEY2": "value2"}.get(name)
        
        mock_keyring.get_password.side_effect = mock_get_password
        
        store_dir = tmp_path / ".secrets"
        store_dir.mkdir()
        (store_dir / "metadata.json").write_text(json.dumps({"secrets": ["KEY1", "KEY2"]}))
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", str(store_dir), "export", "-f", "bash"],
        )
        assert result.exit_code == 0
        assert "export KEY1=value1" in result.stdout
        assert "export KEY2=value2" in result.stdout
        assert "WARNING" in result.stderr


def test_export_json(tmp_path: Path):
    """Test export command with JSON format."""
    with patch("secrets_cli.storage.keyring") as mock_keyring:
        def mock_get_password(service: str, name: str):
            return {"KEY1": "value1", "KEY2": "value2"}.get(name)
        
        mock_keyring.get_password.side_effect = mock_get_password
        
        store_dir = tmp_path / ".secrets"
        store_dir.mkdir()
        (store_dir / "metadata.json").write_text(json.dumps({"secrets": ["KEY1", "KEY2"]}))
        
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", str(store_dir), "export", "-f", "json"],
        )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["count"] == 2
        assert output["secrets"]["KEY1"] == "value1"
        assert output["secrets"]["KEY2"] == "value2"


def test_status_json(tmp_path: Path):
    """Test status command with JSON output."""
    with patch("secrets_cli.storage.keyring"):
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", str(tmp_path), "status", "-f", "json"],
        )
        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["service_name"] == "test"
        assert "secrets_file" in output
        assert "secret_count" in output


def test_status_table(tmp_path: Path):
    """Test status command with table output."""
    with patch("secrets_cli.storage.keyring"):
        result = runner.invoke(
            app,
            ["--service-name", "test", "--base-dir", str(tmp_path), "status", "-f", "table"],
        )
        assert result.exit_code == 0
        assert "Service Name: test" in result.stdout
        assert "Secrets Count:" in result.stdout


def test_empty_service_name():
    """Test that empty service name is rejected."""
    result = runner.invoke(
        app,
        ["--service-name", "", "list"],
    )
    assert result.exit_code == 1
    assert "cannot be empty" in result.stdout

