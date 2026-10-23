import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from devbrief.core.discovery import nearest_git_root

NAME = "copilot"

WORKSPACE_STORAGE_DIR = (
    Path.home() / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage"
)


def _workspace_folder(workspace_dir: Path) -> str | None:
    """Each workspaceStorage/<hash>/workspace.json carries a file:// URI
    pointing at the actual project folder for that hash."""
    try:
        data = json.loads((workspace_dir / "workspace.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    folder_uri = data.get("folder")
    if not folder_uri:
        return None
    parsed = urlparse(folder_uri)
    if parsed.scheme != "file":
        return None
    return unquote(parsed.path)


def discover_projects() -> dict[str, list[Path]]:
    """Returns {repo_root_path_str: [chat_session_json_file, ...]} for every
    git repo with a VS Code Copilot Chat session. Only reads finalized
    `*.json` sessions, not the in-progress `*.jsonl` event-log format."""
    mapping: dict[str, list[Path]] = {}
    if not WORKSPACE_STORAGE_DIR.is_dir():
        return mapping

    for workspace_dir in WORKSPACE_STORAGE_DIR.iterdir():
        if not workspace_dir.is_dir():
            continue
        sessions_dir = workspace_dir / "chatSessions"
        if not sessions_dir.is_dir():
            continue
        json_files = sorted(sessions_dir.glob("*.json"))
        if not json_files:
            continue
        folder = _workspace_folder(workspace_dir)
        if folder is None:
            continue
        repo_root = nearest_git_root(Path(folder))
        if repo_root is None:
            continue
        mapping.setdefault(str(repo_root), []).extend(json_files)

    return mapping


def extract_day_text(json_files: list[Path], day: date) -> list[dict]:
    """Merges this repo's own user-authored Copilot Chat prompts for one
    local calendar day, across all of its session files, deduped by
    requestId."""
    entries: list[dict] = []
    seen_ids: set[str] = set()

    for f in json_files:
        try:
            data = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue

        for req in data.get("requests", []):
            ts_ms = req.get("timestamp")
            if not ts_ms:
                continue
            local_dt = datetime.fromtimestamp(ts_ms / 1000).astimezone()
            if local_dt.date() != day:
                continue

            text = ((req.get("message") or {}).get("text") or "").strip()
            req_id = req.get("requestId")
            if not text or (req_id and req_id in seen_ids):
                continue
            if req_id:
                seen_ids.add(req_id)
            entries.append({"time": local_dt, "text": text})

    entries.sort(key=lambda e: e["time"])
    return entries
