"""Account management with file-based persistence."""

import json
import os
import uuid
from pathlib import Path
from filelock import FileLock

import config

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"
ACCOUNTS_LOCK = Path(__file__).parent.parent / "accounts.json.lock"


def _read_accounts_file() -> dict:
    if not ACCOUNTS_FILE.exists():
        return {"accounts": []}
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_accounts_file(data: dict):
    with FileLock(str(ACCOUNTS_LOCK), timeout=10):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _get_credentials(account_id: str) -> dict:
    user = os.getenv(f"ACCOUNT_{account_id}_USER", "")
    passwd = os.getenv(f"ACCOUNT_{account_id}_PASSWD", "")
    return {"user": user, "passwd": passwd}


def verify_credentials(user: str, passwd: str) -> list[str]:
    """Verify credentials against all accounts.

    Returns list of account IDs whose stored credentials match.
    """
    data = _read_accounts_file()
    matched = []
    for acc in data.get("accounts", []):
        creds = _get_credentials(acc["id"])
        if creds["user"] and creds["user"] == user and creds["passwd"] == passwd:
            matched.append(acc["id"])
    return matched


def load_accounts() -> list[dict]:
    data = _read_accounts_file()
    accounts = []
    for acc in data.get("accounts", []):
        creds = _get_credentials(acc["id"])
        accounts.append({**acc, "credentials": creds})
    return accounts


def get_account(account_id: str) -> dict | None:
    data = _read_accounts_file()
    for acc in data.get("accounts", []):
        if acc["id"] == account_id:
            creds = _get_credentials(account_id)
            return {**acc, "credentials": creds}
    return None


def add_account(
    label: str,
    desks: list[str],
    days_ahead: int = config.DEFAULT_DAYS_AHEAD,
    start_time: str = config.DEFAULT_START_TIME,
    end_time: str = config.DEFAULT_END_TIME,
    site_params: dict | None = None,
    enabled: bool = True,
) -> dict:
    account_id = str(uuid.uuid4())[:8]
    account = {
        "id": account_id,
        "label": label,
        "enabled": enabled,
        "preferences": {
            "desks": desks,
            "days_ahead": days_ahead,
            "start_time": start_time,
            "end_time": end_time,
            "site_params": site_params or dict(config.DEFAULT_SITE_PARAMS),
        },
        "schedules": [],
    }
    data = _read_accounts_file()
    data["accounts"].append(account)
    _write_accounts_file(data)
    return account


def update_account(account_id: str, updates: dict) -> dict | None:
    data = _read_accounts_file()
    for i, acc in enumerate(data["accounts"]):
        if acc["id"] == account_id:
            # Merge updates
            if "label" in updates:
                acc["label"] = updates["label"]
            if "enabled" in updates:
                acc["enabled"] = updates["enabled"]
            if "preferences" in updates:
                acc.setdefault("preferences", {})
                acc["preferences"].update(updates["preferences"])
            data["accounts"][i] = acc
            _write_accounts_file(data)
            return acc
    return None


def delete_account(account_id: str) -> bool:
    data = _read_accounts_file()
    original_len = len(data["accounts"])
    data["accounts"] = [a for a in data["accounts"] if a["id"] != account_id]
    if len(data["accounts"]) < original_len:
        _write_accounts_file(data)
        return True
    return False


def set_credentials(account_id: str, user: str, passwd: str):
    """Write credentials to .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    user_key = f"ACCOUNT_{account_id}_USER"
    passwd_key = f"ACCOUNT_{account_id}_PASSWD"

    # Remove existing entries for this account
    lines = [
        l for l in lines
        if not l.strip().startswith(user_key + "=")
        and not l.strip().startswith(passwd_key + "=")
    ]

    # Append new credentials
    lines.append(f"{user_key}={user}\n")
    lines.append(f"{passwd_key}={passwd}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Update runtime env
    os.environ[user_key] = user
    os.environ[passwd_key] = passwd


def remove_credentials(account_id: str):
    """Remove credentials from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return

    user_key = f"ACCOUNT_{account_id}_USER"
    passwd_key = f"ACCOUNT_{account_id}_PASSWD"

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    lines = [
        l for l in lines
        if not l.strip().startswith(user_key + "=")
        and not l.strip().startswith(passwd_key + "=")
    ]

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    os.environ.pop(user_key, None)
    os.environ.pop(passwd_key, None)


# --- Schedule Management ---

def add_schedule(account_id: str, cron: str, description: str = "", enabled: bool = True) -> dict | None:
    data = _read_accounts_file()
    for acc in data["accounts"]:
        if acc["id"] == account_id:
            schedule = {
                "id": str(uuid.uuid4())[:8],
                "cron": cron,
                "description": description,
                "enabled": enabled,
            }
            acc.setdefault("schedules", []).append(schedule)
            _write_accounts_file(data)
            return schedule
    return None


def update_schedule(account_id: str, schedule_id: str, updates: dict) -> dict | None:
    data = _read_accounts_file()
    for acc in data["accounts"]:
        if acc["id"] == account_id:
            for i, sched in enumerate(acc.get("schedules", [])):
                if sched["id"] == schedule_id:
                    sched.update(updates)
                    acc["schedules"][i] = sched
                    _write_accounts_file(data)
                    return sched
    return None


def delete_schedule(account_id: str, schedule_id: str) -> bool:
    data = _read_accounts_file()
    for acc in data["accounts"]:
        if acc["id"] == account_id:
            original = len(acc.get("schedules", []))
            acc["schedules"] = [s for s in acc.get("schedules", []) if s["id"] != schedule_id]
            if len(acc["schedules"]) < original:
                _write_accounts_file(data)
                return True
    return False
