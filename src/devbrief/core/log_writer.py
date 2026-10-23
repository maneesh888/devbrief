import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from devbrief.core.config import LOG_PATH

_HEADER_RE = re.compile(r"^=== (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+?) ===$")


@dataclass
class LogEntry:
    entry_date: date
    repo_name: str
    repo_root: str
    text: str


def _header(repo_root: str, day: date) -> str:
    return f"=== {day.isoformat()} | {Path(repo_root).name} | {repo_root} ==="


def append(repo_root: str, day: date, paragraph: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(_header(repo_root, day) + "\n")
        f.write(paragraph.strip() + "\n\n")


def read_all() -> list[LogEntry]:
    if not LOG_PATH.exists():
        return []
    entries: list[LogEntry] = []
    current_header: tuple[date, str, str] | None = None
    current_lines: list[str] = []

    def flush():
        if current_header is not None:
            text = "\n".join(current_lines).strip()
            entries.append(LogEntry(current_header[0], current_header[1], current_header[2], text))

    for raw_line in LOG_PATH.read_text().splitlines():
        match = _HEADER_RE.match(raw_line)
        if match:
            flush()
            current_header = (date.fromisoformat(match.group(1)), match.group(2), match.group(3))
            current_lines = []
        elif current_header is not None:
            current_lines.append(raw_line)
    flush()
    return entries


def read_filtered(project: str | None = None, since: date | None = None, limit: int | None = None) -> list[LogEntry]:
    entries = read_all()
    if project:
        entries = [e for e in entries if project in (e.repo_name, e.repo_root)]
    if since:
        entries = [e for e in entries if e.entry_date >= since]
    entries.sort(key=lambda e: e.entry_date, reverse=True)
    if limit:
        entries = entries[:limit]
    return entries


def _rewrite(entries: list[LogEntry]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries.sort(key=lambda e: e.entry_date)
    with LOG_PATH.open("w") as f:
        for e in entries:
            f.write(_header(e.repo_root, e.entry_date) + "\n")
            f.write(e.text + "\n\n")


def prune_older_than(retention_days: int) -> int:
    """Removes log entries older than `retention_days`. Returns the count removed."""
    if not LOG_PATH.exists():
        return 0
    cutoff = date.today() - timedelta(days=retention_days)
    entries = read_all()
    kept = [e for e in entries if e.entry_date >= cutoff]
    removed = len(entries) - len(kept)
    if removed:
        _rewrite(kept)
    return removed


def clear_all() -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
