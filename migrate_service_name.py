#!/usr/bin/env python3
"""
Migration script to copy secrets from old default 'ai-keys' to new 'ai-secrets'.

Usage:
    uv run python migrate_service_name.py
"""

from ai_secrets.storage import SecretsStore


def migrate():
    """Migrate secrets from ai-keys to ai-secrets."""
    old_store = SecretsStore(service_name="ai-keys")
    new_store = SecretsStore(service_name="ai-secrets")
    
    old_secrets = old_store.list_names()
    
    if not old_secrets:
        print("✓ No secrets found in old 'ai-keys' service")
        return
    
    print(f"Found {len(old_secrets)} secrets in 'ai-keys':")
    for name in old_secrets:
        print(f"  - {name}")
    
    print("\nMigrating...")
    migrated = 0
    
    for name in old_secrets:
        value = old_store.get(name)
        if value:
            new_store.set(name, value)
            migrated += 1
            print(f"  ✓ {name}")
        else:
            print(f"  ⚠ {name} (could not read value)")
    
    print(f"\n✓ Migrated {migrated}/{len(old_secrets)} secrets to 'ai-secrets'")
    print("\nYour old secrets in 'ai-keys' are still there.")
    print("You can delete them with:")
    print("  uv run python -m ai_secrets --service-name ai-keys delete SECRET_NAME --yes")

if __name__ == "__main__":
    migrate()

