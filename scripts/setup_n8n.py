"""
setup_n8n.py — Create n8n owner account via API (one-time only)
Run after `docker compose up -d`.

Usage:
  python3 scripts/setup_n8n.py

Default credentials created:
  Email:    admin@local.ai
  Password: Admin12345
"""

import json
import sys
import urllib.request
import urllib.error

N8N_URL = "http://localhost:5678"
OWNER_EMAIL = "admin@local.ai"
OWNER_FIRST = "Admin"
OWNER_LAST = "User"
OWNER_PASSWORD = "Admin12345"


def check_setup_needed() -> bool:
    req = urllib.request.Request(f"{N8N_URL}/rest/settings")
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
            return data.get("data", {}).get("userManagement", {}).get(
                "showSetupOnFirstLoad", True
            )
    except Exception as e:
        print(f"ERROR: Could not reach n8n at {N8N_URL} — {e}")
        sys.exit(1)


def create_owner():
    payload = {
        "email": OWNER_EMAIL,
        "firstName": OWNER_FIRST,
        "lastName": OWNER_LAST,
        "password": OWNER_PASSWORD,
    }
    req = urllib.request.Request(
        f"{N8N_URL}/rest/owner/setup",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
            email = result.get("data", {}).get("email", "")
            print(f"  Owner account created: {email}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Error {e.code}: {body[:200]}")
        sys.exit(1)


def main():
    print("Setting up n8n...")

    if not check_setup_needed():
        print("  n8n already configured — nothing to do")
        print(f"\n  Login at: http://localhost:5678")
        print(f"  Email:    {OWNER_EMAIL}")
        print(f"  Password: {OWNER_PASSWORD}")
        return

    create_owner()
    print(f"\n  Login at: http://localhost:5678")
    print(f"  Email:    {OWNER_EMAIL}")
    print(f"  Password: {OWNER_PASSWORD}")


if __name__ == "__main__":
    main()
