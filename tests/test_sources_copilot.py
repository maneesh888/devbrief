import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from devbrief.core.sources import copilot


def _ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def _make_workspace(workspace_storage: Path, hash_name: str, folder: Path) -> Path:
    workspace_dir = workspace_storage / hash_name
    (workspace_dir / "chatSessions").mkdir(parents=True)
    (workspace_dir / "workspace.json").write_text(
        json.dumps({"folder": f"file://{quote(str(folder))}"})
    )
    return workspace_dir


def _write_session(sessions_dir: Path, name: str, requests: list[tuple[str, str]]) -> Path:
    """requests: list of (text, iso_timestamp)."""
    data = {
        "version": 3, "sessionId": name,
        "requests": [
            {"requestId": f"req_{i}", "message": {"text": text}, "timestamp": _ms(ts)}
            for i, (text, ts) in enumerate(requests)
        ],
    }
    f = sessions_dir / f"{name}.json"
    f.write_text(json.dumps(data))
    return f


def test_discover_projects_resolves_folder_via_workspace_json(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    storage = tmp_path / "workspaceStorage"
    workspace_dir = _make_workspace(storage, "hash1", repo)
    monkeypatch.setattr(copilot, "WORKSPACE_STORAGE_DIR", storage)

    f = _write_session(workspace_dir / "chatSessions", "s1", [("hello", "2026-01-15T09:00:00Z")])

    mapping = copilot.discover_projects()
    assert str(repo) in mapping
    assert mapping[str(repo)] == [f]


def test_discover_projects_skips_non_git_folder(tmp_path, monkeypatch):
    non_git = tmp_path / "no-git-here"
    non_git.mkdir()

    storage = tmp_path / "workspaceStorage"
    workspace_dir = _make_workspace(storage, "hash1", non_git)
    monkeypatch.setattr(copilot, "WORKSPACE_STORAGE_DIR", storage)
    _write_session(workspace_dir / "chatSessions", "s1", [("hello", "2026-01-15T09:00:00Z")])

    assert copilot.discover_projects() == {}


def test_discover_projects_ignores_jsonl_live_sessions(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    storage = tmp_path / "workspaceStorage"
    workspace_dir = _make_workspace(storage, "hash1", repo)
    monkeypatch.setattr(copilot, "WORKSPACE_STORAGE_DIR", storage)
    (workspace_dir / "chatSessions" / "live.jsonl").write_text('{"kind": 0, "v": {}}\n')

    assert copilot.discover_projects() == {}


def test_extract_day_text_picks_matching_day(tmp_path):
    f = _write_session(tmp_path, "s1", [
        ("fix the login bug", "2026-01-15T10:00:00Z"),
        ("other day message", "2026-01-16T10:00:00Z"),
    ])

    entries = copilot.extract_day_text([f], date(2026, 1, 15))
    assert [e["text"] for e in entries] == ["fix the login bug"]


def test_extract_day_text_dedupes_by_request_id_across_files(tmp_path):
    f1 = _write_session(tmp_path, "s1", [("same message", "2026-01-15T09:00:00Z")])
    f2 = tmp_path / "s2.json"
    f2.write_text(f1.read_text())  # same requestId ("req_0") in a second file

    entries = copilot.extract_day_text([f1, f2], date(2026, 1, 15))
    assert len(entries) == 1


def test_extract_day_text_sorted_by_time(tmp_path):
    f = _write_session(tmp_path, "s1", [
        ("second", "2026-01-15T12:00:00Z"),
        ("first", "2026-01-15T09:00:00Z"),
    ])

    entries = copilot.extract_day_text([f], date(2026, 1, 15))
    assert [e["text"] for e in entries] == ["first", "second"]
