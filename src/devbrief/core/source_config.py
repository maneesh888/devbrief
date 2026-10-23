import json
import os
import sys

from devbrief.core.config import SOURCES_PATH

DEFAULT_SOURCES = {"claude_code": True, "codex": True, "copilot": True}


def load() -> dict[str, bool]:
    """Returns the enabled/disabled state for every known source. Unknown
    keys in the file are dropped; missing keys fall back to the default."""
    if not SOURCES_PATH.exists():
        return dict(DEFAULT_SOURCES)
    try:
        data = json.loads(SOURCES_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        print(f"warning: {SOURCES_PATH} is unreadable/corrupt, using defaults", file=sys.stderr)
        return dict(DEFAULT_SOURCES)
    merged = dict(DEFAULT_SOURCES)
    merged.update({k: bool(v) for k, v in data.items() if k in DEFAULT_SOURCES})
    return merged


def enabled_names() -> list[str]:
    return [name for name, on in load().items() if on]


def set_enabled(name: str, enabled: bool) -> None:
    if name not in DEFAULT_SOURCES:
        raise ValueError(f"unknown source: {name!r} (known: {sorted(DEFAULT_SOURCES)})")
    data = load()
    data[name] = enabled
    SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SOURCES_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True))
    os.replace(tmp_path, SOURCES_PATH)
