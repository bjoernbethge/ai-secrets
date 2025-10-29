#!/usr/bin/env python3
"""
Cleanup script to delete old secrets from 'ai-keys' service.

WARNING: This will permanently delete secrets from the old 'ai-keys' service!
Make sure you've migrated to 'ai-secrets' first.

Usage:
    uv run python cleanup_old_service.py
"""

from ai_secrets.storage import SecretsStore

def cleanup():
    """Delete all secrets from old 'ai-keys' service."""
    old_store = SecretsStore(service_name="ai-keys")
    old_secrets = old_store.list_names()
    
    if not old_secrets:
        print("✓ No secrets found in old 'ai-keys' service - already clean!")
        return
    
    print(f"⚠️  WARNING: About to delete {len(old_secrets)} secrets from 'ai-keys':")
    for name in old_secrets:
        print(f"  - {name}")
    
    response = input("\nAre you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("Cancelled - no secrets deleted")
        return
    
    print("\nDeleting...")
    deleted = 0
    
    for name in old_secrets:
        if old_store.delete(name):
            deleted += 1
            print(f"  ✓ Deleted {name}")
        else:
            print(f"  ⚠ Failed to delete {name}")
    
    print(f"\n✓ Deleted {deleted}/{len(old_secrets)} secrets from 'ai-keys'")
    print("Your new secrets in 'ai-secrets' are unaffected.")

if __name__ == "__main__":
    cleanup()

