import json
from pathlib import Path

from devbrief.core import discovery


def test_nearest_git_root_finds_dir_style_git(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    sub = repo / "sub" / "deeper"
    sub.mkdir(parents=True)
    assert discovery.nearest_git_root(sub) == repo


def test_nearest_git_root_finds_worktree_file_style_git(tmp_path):
    repo = tmp_path / "worktree-repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /somewhere/else\n")
    assert discovery.nearest_git_root(repo) == repo


def test_nearest_git_root_returns_none_when_no_git(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert discovery.nearest_git_root(plain) is None


def test_discover_projects_merges_duplicate_cwd_folders(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    projects_dir = tmp_path / "claude-projects"
    projects_dir.mkdir()
    monkeypatch.setattr(discovery, "PROJECTS_DIR", projects_dir)

    folder_a = projects_dir / "-sanitized-a"
    folder_a.mkdir()
    (folder_a / "session1.jsonl").write_text(
        json.dumps({"type": "user", "cwd": str(repo), "timestamp": "2026-01-01T00:00:00Z"}) + "\n"
    )

    folder_b = projects_dir / "-sanitized-b"
    folder_b.mkdir()
    (folder_b / "session2.jsonl").write_text(
        json.dumps({"type": "user", "cwd": str(repo), "timestamp": "2026-01-01T00:00:00Z"}) + "\n"
    )

    mapping = discovery.discover_projects()
    assert str(repo) in mapping
    assert len(mapping[str(repo)]) == 2


def test_discover_projects_skips_non_git_cwd(tmp_path, monkeypatch):
    non_git = tmp_path / "no-git-here"
    non_git.mkdir()

    projects_dir = tmp_path / "claude-projects"
    projects_dir.mkdir()
    monkeypatch.setattr(discovery, "PROJECTS_DIR", projects_dir)

    folder = projects_dir / "-sanitized"
    folder.mkdir()
    (folder / "session1.jsonl").write_text(
        json.dumps({"type": "user", "cwd": str(non_git), "timestamp": "2026-01-01T00:00:00Z"}) + "\n"
    )

    assert discovery.discover_projects() == {}
