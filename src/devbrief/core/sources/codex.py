import json
from datetime import date, datetime
from pathlib import Path

from devbrief.core.discovery import nearest_git_root

NAME = "codex"

SESSIONS_DIR = Path.home() / ".codex" / "sessions"

# Codex prepends a large tool/plugin-listing block to the first user turn of
# a session, wrapped as its own message. It's not anything the user typed,
# so drop any user message that's entirely this wrapper.
_BOILERPLATE_PREFIXES = ("<recommended_plugins>", "<environment_context>")


def _session_cwd(jsonl_file: Path) -> str | None:
    """Codex's `session_meta` line (first line of a rollout file) carries
    the working directory the session was started in."""
    try:
        with jsonl_file.open() as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    d = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if d.get("type") == "session_meta":
                    cwd = d.get("payload", {}).get("cwd")
                    if cwd:
                        return cwd
                    break
    except OSError:
        pass
    return None


def discover_projects() -> dict[str, list[Path]]:
    """Returns {repo_root_path_str: [rollout_jsonl_file, ...]} for every git
    repo that has Codex session history, under ~/.codex/sessions/YYYY/MM/DD/."""
    mapping: dict[str, list[Path]] = {}
    if not SESSIONS_DIR.is_dir():
        return mapping

    for jsonl_file in SESSIONS_DIR.glob("*/*/*/*.jsonl"):
        cwd = _session_cwd(jsonl_file)
        if cwd is None:
            continue
        repo_root = nearest_git_root(Path(cwd))
        if repo_root is None:
            continue
        mapping.setdefault(str(repo_root), []).append(jsonl_file)

    return mapping


def extract_day_text(jsonl_files: list[Path], day: date) -> list[dict]:
    """Merges this repo's own user-authored Codex turns for one local
    calendar day, across all of its rollout files, deduped by message id."""
    entries: list[dict] = []
    seen_ids: set[str] = set()

    for f in jsonl_files:
        try:
            lines = f.open().readlines()
        except OSError:
            continue
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if d.get("type") != "response_item":
                continue
            payload = d.get("payload", {})
            if payload.get("type") != "message" or payload.get("role") != "user":
                continue

            ts = d.get("timestamp")
            if not ts:
                continue
            try:
                local_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
            except ValueError:
                continue
            if local_dt.date() != day:
                continue

            content = payload.get("content")
            if not isinstance(content, list):
                continue
            text = " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "input_text" and block.get("text")
            ).strip()

            msg_id = payload.get("id")
            if not text or (msg_id and msg_id in seen_ids) or text.startswith(_BOILERPLATE_PREFIXES):
                continue
            if msg_id:
                seen_ids.add(msg_id)
            entries.append({"time": local_dt, "text": text})

    entries.sort(key=lambda e: e["time"])
    return entries
