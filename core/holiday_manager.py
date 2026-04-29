"""Holiday management with file-based persistence."""

import json
import uuid
from datetime import date
from pathlib import Path
from filelock import FileLock

import config

HOLIDAYS_FILE = config.HOLIDAYS_FILE
HOLIDAYS_LOCK = Path(str(HOLIDAYS_FILE) + ".lock")


def _read_holidays_file() -> dict:
    if not HOLIDAYS_FILE.exists():
        return {"holidays": []}
    with open(HOLIDAYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_holidays_file(data: dict):
    with FileLock(str(HOLIDAYS_LOCK), timeout=10):
        with open(HOLIDAYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def list_holidays() -> list[dict]:
    data = _read_holidays_file()
    return data.get("holidays", [])


def get_holiday(holiday_id: str) -> dict | None:
    for h in list_holidays():
        if h["id"] == holiday_id:
            return h
    return None


def add_holiday(date_str: str, description: str) -> dict:
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str!r}. Expected YYYY-MM-DD.")

    if target < date.today():
        raise ValueError(f"Cannot add a holiday in the past: {date_str}")

    data = _read_holidays_file()
    for h in data.get("holidays", []):
        if h["date"] == date_str:
            raise ValueError(f"date already exists: {date_str}")

    holiday = {
        "id": str(uuid.uuid4())[:8],
        "date": date_str,
        "description": description,
    }
    data.setdefault("holidays", []).append(holiday)
    _write_holidays_file(data)
    return holiday


def update_holiday(holiday_id: str, date_str: str | None = None, description: str | None = None) -> dict:
    data = _read_holidays_file()
    for i, h in enumerate(data.get("holidays", [])):
        if h["id"] == holiday_id:
            if date_str is not None:
                try:
                    target = date.fromisoformat(date_str)
                except ValueError:
                    raise ValueError(f"Invalid date format: {date_str!r}. Expected YYYY-MM-DD.")
                if target < date.today():
                    raise ValueError(f"Cannot set a holiday to a past date: {date_str}")
                # Reject duplicate date (excluding the holiday being updated)
                for other in data["holidays"]:
                    if other["id"] != holiday_id and other["date"] == date_str:
                        raise ValueError(f"date already exists: {date_str}")
                h["date"] = date_str
            if description is not None:
                h["description"] = description
            data["holidays"][i] = h
            _write_holidays_file(data)
            return h
    raise KeyError(f"Holiday not found: {holiday_id}")


def delete_holiday(holiday_id: str) -> bool:
    data = _read_holidays_file()
    original_len = len(data.get("holidays", []))
    data["holidays"] = [h for h in data.get("holidays", []) if h["id"] != holiday_id]
    if len(data["holidays"]) < original_len:
        _write_holidays_file(data)
        return True
    return False


def is_holiday(target_date: date) -> bool:
    date_str = target_date.isoformat()
    return any(h["date"] == date_str for h in list_holidays())
