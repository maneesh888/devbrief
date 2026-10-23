import json
import subprocess
from pathlib import Path

import pytest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def fake_repo(tmp_path):
    repo = tmp_path / "fake-repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tester@example.com")
    _git(repo, "config", "user.name", "Tester")
    (repo / "file.txt").write_text("hello\n")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-q", "-m", "Initial commit")
    return repo


def write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


@pytest.fixture
def user_line_factory():
    def _make(text: str, timestamp: str, uuid: str = "u1", is_meta: bool = False) -> dict:
        return {
            "type": "user",
            "isMeta": is_meta,
            "uuid": uuid,
            "parentUuid": None,
            "timestamp": timestamp,
            "sessionId": "session-1",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        }
    return _make
