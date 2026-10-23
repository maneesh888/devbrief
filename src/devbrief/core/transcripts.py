import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

# Claude Code system-generated markers that land in "user" turns but aren't
# anything the user actually typed (e.g. a tool-use interruption banner).
_SYSTEM_MARKER_RE = re.compile(r"^\[Request interrupted.*\]$")


def _lines_for_day(jsonl_files: list[Path], day: date) -> Iterator[dict]:
    """Yields every parsed JSON line (any type) whose timestamp falls on `day`."""
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

            ts = d.get("timestamp")
            if not ts:
                continue
            try:
                local_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
            except ValueError:
                continue
            if local_dt.date() != day:
                continue

            d["_local_dt"] = local_dt
            yield d


def extract_day_text(jsonl_files: list[Path], day: date) -> list[dict]:
    """Merges this repo's own user-authored transcript text for one local
    calendar day, across all of its session files, deduped by message uuid."""
    entries: list[dict] = []
    seen_uuids: set[str] = set()

    for d in _lines_for_day(jsonl_files, day):
        if d.get("type") != "user" or d.get("isMeta"):
            continue

        content = d.get("message", {}).get("content")
        if not isinstance(content, list):
            # Plain-string content is a slash-command literal; skip it.
            continue

        text = " ".join(
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        ).strip()

        uid = d.get("uuid")
        if not text or (uid and uid in seen_uuids) or _SYSTEM_MARKER_RE.match(text):
            continue
        if uid:
            seen_uuids.add(uid)
        entries.append({"time": d["_local_dt"], "text": text})

    entries.sort(key=lambda e: e["time"])
    return entries


def dominant_branch(jsonl_files: list[Path], day: date) -> str | None:
    """The most common `gitBranch` value across that day's transcript lines —
    a cheap, honest signal of what initiative/branch the work belongs to,
    for the summarizer to use as framing context (never invented)."""
    counts = Counter(
        d["gitBranch"] for d in _lines_for_day(jsonl_files, day) if d.get("gitBranch")
    )
    return counts.most_common(1)[0][0] if counts else None
