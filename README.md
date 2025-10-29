# ai-secrets

AI-friendly secrets management CLI using OS-native encryption.

**Supported Backends:**  
Windows Credential Manager • macOS Keychain • Linux Secret Service

## Features

- 🔒 **Secure** — OS-native keyring encryption
- 🤖 **AI-friendly** — Consistent JSON with `success` flags, `--reveal` mode
- 📊 **Flexible** — JSON, Table, and Bash output formats
- 🎯 **Type-safe** — Full type hints and validation
- ✅ **Tested** — 34 passing tests
- 🚀 **Simple** — Clean API with proper error handling

## Installation

```bash
# From PyPI
pip install ai-secrets

# Or with uv
uv pip install ai-secrets

# Development install
git clone https://github.com/BjornBethge/ai-secrets.git
cd ai-secrets
uv pip install -e .
```

## Quick Start

```bash
# Store a secret
ai-secrets set HF_TOKEN "hf_your_token_here"

# Check if secret exists
ai-secrets get HF_TOKEN

# List all secrets (names only)
ai-secrets list

# AI-friendly: Get secret value in JSON
ai-secrets get HF_TOKEN --reveal -f json

# Delete secret
ai-secrets delete HF_TOKEN --yes
```

> **Note:** The command `secrets` is also available as an alias for `ai-secrets`.

## Commands

### `set` — Store secret
```bash
ai-secrets set API_KEY "sk-1234" -f json
# {"success": true, "name": "API_KEY", "message": "..."}
```

### `get` — Retrieve secret
```bash
# Check existence only
ai-secrets get API_KEY
# ✓ Secret 'API_KEY' exists

# For AI workflows (returns value in JSON)
ai-secrets get API_KEY --reveal -f json
# {"success": true, "name": "API_KEY", "exists": true, "value": "sk-1234"}

# For humans (prints to terminal)
ai-secrets get API_KEY --print
```

### `list` — List all secrets
```bash
ai-secrets list -f json
# {"success": true, "secrets": ["API_KEY", "HF_TOKEN"], "count": 2}
```

### `delete` — Delete secret
```bash
ai-secrets delete API_KEY --yes -f json
# {"success": true, "name": "API_KEY", "deleted": true}
```

### `status` — Show manager status
```bash
ai-secrets status -f json
# {"success": true, "service_name": "ai-keys", "secret_count": 3, ...}
```

### `export` — Export as environment variables
```bash
# Bash format (prints export statements)
ai-secrets export -f bash
# export API_KEY=sk-1234
# export HF_TOKEN=hf_xxx

# JSON format
ai-secrets export -f json
# {"success": true, "secrets": {"API_KEY": "sk-1234", ...}, "count": 2}
```

## AI-Friendly JSON

All JSON responses follow a consistent structure:

**Success:**
```json
{
  "success": true,
  "name": "API_KEY",
  ...
}
```

**Error:**
```json
{
  "success": false,
  "error": "Secret 'MISSING' not found",
  "name": "MISSING"
}
```

**The `--reveal` flag:**
- Works only with `-f json`
- Returns actual secret value
- Designed for AI workflows where value is needed programmatically

## Multi-Project Support

Use `--service-name` to isolate secrets per project:

```bash
# Production secrets
ai-secrets --service-name myapp-prod set DB_PASSWORD "secret"

# Development secrets  
ai-secrets --service-name myapp-dev set DB_PASSWORD "dev123"

# Custom metadata location
ai-secrets --service-name myapp --base-dir .secrets set API_KEY "key"
```

**Python API:**
```python
from ai_secrets.storage import SecretsStore
from pathlib import Path

# Per-environment stores
prod_store = SecretsStore(service_name="myapp-prod")
dev_store = SecretsStore(service_name="myapp-dev", base_dir=Path(".secrets"))

# Set and get secrets
prod_store.set("API_KEY", "sk-prod-xxx")
print(prod_store.get("API_KEY"))  # "sk-prod-xxx"

# List all secret names
secrets = prod_store.list_names()  # ["API_KEY", ...]

# Export as dict
env_vars = prod_store.export_env()  # {"API_KEY": "sk-prod-xxx", ...}

# Delete a secret
prod_store.delete("API_KEY")
```

**Direct keyring usage:**
```python
import keyring

# Store secret (basic keyring API)
keyring.set_password("myapp", "API_KEY", "secret-value")

# Get secret
value = keyring.get_password("myapp", "API_KEY")

# Delete secret
keyring.delete_password("myapp", "API_KEY")
```

> **Why use ai-secrets instead of raw keyring?**
> - ✅ Secret name management (list all secrets)
> - ✅ Metadata tracking (knows what secrets exist)
> - ✅ Multi-environment support (`--service-name`)
> - ✅ JSON export for AI workflows
> - ✅ CLI convenience

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Install in dev mode
uv pip install -e .
```

## Notes

- Default service name: `ai-keys`
- Metadata stored in: `~/.secrets/metadata.json` (only names, not values)
- Secret values stored in: OS keyring (encrypted)
- `export -f bash` prints warning to stderr
- Linux/KeePassXC: May prompt for database unlock
