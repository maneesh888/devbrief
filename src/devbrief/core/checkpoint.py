import json
import os
import sys
from datetime import date, datetime, timezone

from devbrief.core.config import CHECKPOINT_PATH

DONE_STATUSES = {"generated", "skipped_no_activity"}


def _load() -> dict:
    if not CHECKPOINT_PATH.exists():
        return {}
    try:
        return json.loads(CHECKPOINT_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        print(f"warning: {CHECKPOINT_PATH} is unreadable/corrupt, treating as empty", file=sys.stderr)
        return {}


def _save(data: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CHECKPOINT_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True))
    os.replace(tmp_path, CHECKPOINT_PATH)


def is_processed(repo_root: str, day: date) -> bool:
    data = _load()
    record = data.get(repo_root, {}).get(day.isoformat())
    return bool(record and record.get("status") in DONE_STATUSES)


def mark(repo_root: str, day: date, status: str, **extra) -> None:
    data = _load()
    data.setdefault(repo_root, {})[day.isoformat()] = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    _save(data)


def all_entries() -> dict:
    return _load()


def clear() -> None:
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
