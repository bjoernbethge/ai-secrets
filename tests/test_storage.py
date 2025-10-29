from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_secrets.storage import SecretsStore


@pytest.fixture
def temp_store(tmp_path: Path) -> SecretsStore:
    """Create a temporary SecretsStore for testing."""
    return SecretsStore(service_name="test-service", base_dir=tmp_path / ".secrets")


@pytest.fixture
def mock_keyring():
    """Mock the keyring module."""
    with patch("ai_secrets.storage.keyring") as mock:
        storage = {}
        
        def set_password(service: str, name: str, value: str) -> None:
            storage[f"{service}:{name}"] = value
        
        def get_password(service: str, name: str) -> str | None:
            return storage.get(f"{service}:{name}")
        
        def delete_password(service: str, name: str) -> None:
            key = f"{service}:{name}"
            if key in storage:
                del storage[key]
        
        mock.set_password = Mock(side_effect=set_password)
        mock.get_password = Mock(side_effect=get_password)
        mock.delete_password = Mock(side_effect=delete_password)
        
        yield mock


def test_init_default():
    """Test initialization with default parameters."""
    store = SecretsStore()
    assert store.service_name == "ai-keys"
    assert store.base_dir == Path.home() / ".secrets"
    assert store.metadata_file == store.base_dir / "metadata.json"


def test_init_custom(tmp_path: Path):
    """Test initialization with custom parameters."""
    custom_dir = tmp_path / "custom"
    store = SecretsStore(service_name="my-service", base_dir=custom_dir)
    assert store.service_name == "my-service"
    assert store.base_dir == custom_dir
    assert store.metadata_file == custom_dir / "metadata.json"


def test_init_empty_service_name():
    """Test that empty service_name raises ValueError."""
    with pytest.raises(ValueError, match="service_name cannot be empty"):
        SecretsStore(service_name="")
    
    with pytest.raises(ValueError, match="service_name cannot be empty"):
        SecretsStore(service_name="   ")


def test_set_and_get(temp_store: SecretsStore, mock_keyring):
    """Test storing and retrieving a secret."""
    temp_store.set("TEST_KEY", "test_value")
    
    mock_keyring.set_password.assert_called_once_with("test-service", "TEST_KEY", "test_value")
    
    value = temp_store.get("TEST_KEY")
    assert value == "test_value"
    
    assert temp_store.metadata_file.exists()
    metadata = json.loads(temp_store.metadata_file.read_text())
    assert "TEST_KEY" in metadata["secrets"]


def test_set_empty_name(temp_store: SecretsStore, mock_keyring):
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="Secret name cannot be empty"):
        temp_store.set("", "value")
    
    with pytest.raises(ValueError, match="Secret name cannot be empty"):
        temp_store.set("   ", "value")


def test_set_empty_value(temp_store: SecretsStore, mock_keyring):
    """Test that empty value raises ValueError."""
    with pytest.raises(ValueError, match="Secret value cannot be empty"):
        temp_store.set("KEY", "")


def test_get_nonexistent(temp_store: SecretsStore, mock_keyring):
    """Test retrieving a non-existent secret."""
    value = temp_store.get("NONEXISTENT")
    assert value is None


def test_get_empty_name(temp_store: SecretsStore, mock_keyring):
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="Secret name cannot be empty"):
        temp_store.get("")


def test_list_names_empty(temp_store: SecretsStore):
    """Test listing names when no secrets exist."""
    names = temp_store.list_names()
    assert names == []


def test_list_names(temp_store: SecretsStore, mock_keyring):
    """Test listing secret names."""
    temp_store.set("KEY1", "value1")
    temp_store.set("KEY2", "value2")
    temp_store.set("KEY3", "value3")
    
    names = temp_store.list_names()
    assert set(names) == {"KEY1", "KEY2", "KEY3"}


def test_delete(temp_store: SecretsStore, mock_keyring):
    """Test deleting a secret."""
    temp_store.set("DELETE_ME", "value")
    assert temp_store.get("DELETE_ME") == "value"
    
    result = temp_store.delete("DELETE_ME")
    assert result is True
    
    assert temp_store.get("DELETE_ME") is None
    assert "DELETE_ME" not in temp_store.list_names()


def test_delete_nonexistent(temp_store: SecretsStore, mock_keyring):
    """Test deleting a non-existent secret."""
    result = temp_store.delete("NONEXISTENT")
    assert result is False


def test_delete_empty_name(temp_store: SecretsStore, mock_keyring):
    """Test that empty name raises ValueError."""
    with pytest.raises(ValueError, match="Secret name cannot be empty"):
        temp_store.delete("")


def test_export_env(temp_store: SecretsStore, mock_keyring):
    """Test exporting secrets as environment variables."""
    temp_store.set("KEY1", "value1")
    temp_store.set("KEY2", "value2")
    temp_store.set("KEY3", "value3")
    
    exports = temp_store.export_env()
    assert exports == {
        "KEY1": "value1",
        "KEY2": "value2",
        "KEY3": "value3",
    }


def test_export_env_empty(temp_store: SecretsStore, mock_keyring):
    """Test exporting when no secrets exist."""
    exports = temp_store.export_env()
    assert exports == {}


def test_metadata_file_created(temp_store: SecretsStore, mock_keyring):
    """Test that metadata file is created when storing secrets."""
    temp_store.set("KEY", "value")
    
    assert temp_store.metadata_file.exists()
    assert temp_store.base_dir.exists()
    
    # Verify metadata file contains the secret name
    metadata = json.loads(temp_store.metadata_file.read_text())
    assert "KEY" in metadata["secrets"]


def test_duplicate_secret_update_metadata_once(temp_store: SecretsStore, mock_keyring):
    """Test that setting the same secret twice doesn't duplicate in metadata."""
    temp_store.set("KEY", "value1")
    temp_store.set("KEY", "value2")
    
    names = temp_store.list_names()
    assert names.count("KEY") == 1
    assert temp_store.get("KEY") == "value2"


def test_metadata_file_invalid_json(temp_store: SecretsStore, mock_keyring):
    """Test handling of corrupted metadata file."""
    temp_store.base_dir.mkdir(exist_ok=True)
    temp_store.metadata_file.write_text("invalid json{")
    
    with pytest.raises(ValueError, match="Invalid JSON"):
        temp_store.list_names()


def test_metadata_file_legacy_dict_format(temp_store: SecretsStore, mock_keyring):
    """Test compatibility with old dict-based metadata format."""
    temp_store.base_dir.mkdir(exist_ok=True)
    temp_store.metadata_file.write_text(json.dumps({
        "secrets": {"KEY1": {}, "KEY2": {}}
    }))
    
    names = temp_store.list_names()
    assert set(names) == {"KEY1", "KEY2"}

