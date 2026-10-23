import json
from datetime import date
from pathlib import Path

from devbrief.core.sources import codex


def _rollout_line(**kwargs) -> dict:
    return kwargs


def _write_rollout(f: Path, cwd: str, user_messages: list[tuple[str, str]]) -> None:
    """user_messages: list of (text, iso_timestamp)."""
    lines = [
        _rollout_line(
            timestamp="2026-01-15T09:00:00.000Z", ordinal=0, type="session_meta",
            payload={"session_id": "s1", "cwd": cwd},
        )
    ]
    for i, (text, ts) in enumerate(user_messages):
        lines.append(_rollout_line(
            timestamp=ts, ordinal=i + 1, type="response_item",
            payload={
                "type": "message", "id": f"msg_{i}", "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        ))
    f.write_text("\n".join(json.dumps(l) for l in lines) + "\n")


def test_discover_projects_finds_repo_from_session_meta_cwd(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    sessions_dir = tmp_path / "codex-sessions"
    day_dir = sessions_dir / "2026" / "01" / "15"
    day_dir.mkdir(parents=True)
    monkeypatch.setattr(codex, "SESSIONS_DIR", sessions_dir)

    f = day_dir / "rollout-1.jsonl"
    _write_rollout(f, str(repo), [("hello", "2026-01-15T09:05:00.000Z")])

    mapping = codex.discover_projects()
    assert str(repo) in mapping
    assert mapping[str(repo)] == [f]


def test_discover_projects_skips_non_git_cwd(tmp_path, monkeypatch):
    non_git = tmp_path / "no-git-here"
    non_git.mkdir()

    sessions_dir = tmp_path / "codex-sessions"
    day_dir = sessions_dir / "2026" / "01" / "15"
    day_dir.mkdir(parents=True)
    monkeypatch.setattr(codex, "SESSIONS_DIR", sessions_dir)

    f = day_dir / "rollout-1.jsonl"
    _write_rollout(f, str(non_git), [("hello", "2026-01-15T09:05:00.000Z")])

    assert codex.discover_projects() == {}


def test_extract_day_text_picks_matching_day_and_filters_boilerplate(tmp_path):
    f = tmp_path / "rollout.jsonl"
    _write_rollout(f, "/repo", [
        ("<recommended_plugins>\nlots of injected tool listing\n</recommended_plugins>", "2026-01-15T09:00:05Z"),
        ("fix the login bug", "2026-01-15T10:00:00Z"),
        ("other day message", "2026-01-16T10:00:00Z"),
    ])

    entries = codex.extract_day_text([f], date(2026, 1, 15))
    assert [e["text"] for e in entries] == ["fix the login bug"]


def test_extract_day_text_dedupes_by_message_id_across_files(tmp_path):
    f1 = tmp_path / "s1.jsonl"
    f2 = tmp_path / "s2.jsonl"
    _write_rollout(f1, "/repo", [("same message", "2026-01-15T09:00:00Z")])
    _write_rollout(f2, "/repo", [("same message", "2026-01-15T09:00:00Z")])

    entries = codex.extract_day_text([f1, f2], date(2026, 1, 15))
    assert len(entries) == 1


def test_extract_day_text_sorted_by_time(tmp_path):
    f = tmp_path / "rollout.jsonl"
    _write_rollout(f, "/repo", [
        ("second", "2026-01-15T12:00:00Z"),
        ("first", "2026-01-15T09:00:00Z"),
    ])

    entries = codex.extract_day_text([f], date(2026, 1, 15))
    assert [e["text"] for e in entries] == ["first", "second"]
