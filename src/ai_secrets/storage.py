from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import keyring


class SecretsStore:
    """Keyring-backed secrets storage with simple metadata index.
    
    Stores secret values in the OS-native keyring (Windows Credential Manager,
    macOS Keychain, Linux Secret Service) and maintains a metadata index file
    with secret names only (not values).
    
    Args:
        service_name: Namespace for storing secrets in keyring (default: "ai-keys")
        base_dir: Directory for metadata file (default: ~/.secrets)
        
    Attributes:
        service_name: The keyring service namespace
        base_dir: Directory containing metadata.json
        metadata_file: Path to metadata index file
    """

    def __init__(
        self, service_name: str = "ai-secrets", base_dir: Optional[Path] = None
    ) -> None:
        if not service_name or not service_name.strip():
            raise ValueError("service_name cannot be empty")
        self.service_name = service_name.strip()
        self.base_dir = base_dir or Path.home() / ".secrets"
        # Service-specific metadata file to avoid conflicts
        safe_service_name = self.service_name.replace("/", "_").replace("\\", "_")
        self.metadata_file = self.base_dir / f"metadata_{safe_service_name}.json"

    def _setup_dirs(self) -> None:
        """Create base directory with secure permissions (0o700)."""
        try:
            self.base_dir.mkdir(mode=0o700, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create directory {self.base_dir}: {e}") from e

    def _load_names(self) -> list[str]:
        """Load secret names from metadata file.
        
        Returns:
            List of secret names, empty list if file doesn't exist or is invalid.
        """
        if not self.metadata_file.exists():
            return []
        try:
            data = json.loads(self.metadata_file.read_text(encoding='utf-8'))
            secrets = data.get("secrets", [])
            if isinstance(secrets, dict):
                return list(secrets.keys())
            if not isinstance(secrets, list):
                return []
            return secrets
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in metadata file {self.metadata_file}: {e}") from e
        except OSError as e:
            raise OSError(f"Failed to read metadata file {self.metadata_file}: {e}") from e

    def _save_names(self, names: list[str]) -> None:
        """Save secret names to metadata file with secure permissions.
        
        Args:
            names: List of secret names to save
            
        Raises:
            OSError: If directory creation or file write fails
        """
        self._setup_dirs()
        try:
            self.metadata_file.write_text(
                json.dumps({"secrets": names}, indent=2), encoding='utf-8'
            )
            self.metadata_file.chmod(0o600)
        except OSError as e:
            raise OSError(f"Failed to write metadata file {self.metadata_file}: {e}") from e

    def set(self, name: str, value: str) -> None:
        """Store secret in OS keyring and update metadata.
        
        Args:
            name: Secret name (e.g., "HF_TOKEN", "OPENAI_API_KEY")
            value: Secret value to store securely
            
        Raises:
            ValueError: If name or value is empty
            OSError: If keyring or metadata update fails
        """
        if not name or not name.strip():
            raise ValueError("Secret name cannot be empty")
        if not value:
            raise ValueError("Secret value cannot be empty")
            
        try:
            keyring.set_password(self.service_name, name.strip(), value)
        except Exception as e:
            raise OSError(f"Failed to store secret in keyring: {e}") from e
            
        names = self._load_names()
        if name not in names:
            names.append(name)
            self._save_names(names)

    def get(self, name: str) -> Optional[str]:
        """Retrieve secret value from OS keyring.
        
        Args:
            name: Secret name to retrieve
            
        Returns:
            Secret value if found, None otherwise
            
        Raises:
            OSError: If keyring access fails
        """
        if not name or not name.strip():
            raise ValueError("Secret name cannot be empty")
            
        try:
            return keyring.get_password(self.service_name, name.strip())
        except Exception as e:
            raise OSError(f"Failed to retrieve secret from keyring: {e}") from e

    def delete(self, name: str) -> bool:
        """Delete secret from OS keyring and metadata.
        
        Args:
            name: Secret name to delete
            
        Returns:
            True if secret was deleted, False if it didn't exist
            
        Raises:
            ValueError: If name is empty
            OSError: If keyring or metadata update fails
        """
        if not name or not name.strip():
            raise ValueError("Secret name cannot be empty")
            
        if self.get(name) is None:
            return False
            
        try:
            keyring.delete_password(self.service_name, name.strip())
        except Exception as e:
            raise OSError(f"Failed to delete secret from keyring: {e}") from e
            
        names = self._load_names()
        if name in names:
            names.remove(name)
            self._save_names(names)
        return True

    def list_names(self) -> list[str]:
        """List all stored secret names (not values).
        
        Returns:
            List of secret names
            
        Raises:
            ValueError: If metadata file is invalid
            OSError: If metadata file cannot be read
        """
        return self._load_names()

    def export_env(self) -> dict[str, str]:
        """Export all secrets as environment variable dictionary.
        
        Returns:
            Dictionary mapping secret names to values
            
        Raises:
            OSError: If keyring access fails
        """
        result: dict[str, str] = {}
        for n in self._load_names():
            v = self.get(n)
            if v:
                result[n] = v
        return result
