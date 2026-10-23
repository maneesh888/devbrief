from datetime import date

from devbrief.core import checkpoint


def test_mark_and_is_processed(monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint, "CHECKPOINT_PATH", tmp_path / "checkpoint.json")
    day = date(2026, 1, 15)

    assert checkpoint.is_processed("/repo", day) is False
    checkpoint.mark("/repo", day, status="generated", commit_count=2)
    assert checkpoint.is_processed("/repo", day) is True


def test_non_generated_status_is_not_processed(monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint, "CHECKPOINT_PATH", tmp_path / "checkpoint.json")
    day = date(2026, 1, 15)

    checkpoint.mark("/repo", day, status="something-else")
    assert checkpoint.is_processed("/repo", day) is False


def test_corrupt_checkpoint_treated_as_empty(monkeypatch, tmp_path):
    path = tmp_path / "checkpoint.json"
    path.write_text("{not valid json")
    monkeypatch.setattr(checkpoint, "CHECKPOINT_PATH", path)

    assert checkpoint.is_processed("/repo", date(2026, 1, 15)) is False


def test_clear_removes_file(monkeypatch, tmp_path):
    path = tmp_path / "checkpoint.json"
    monkeypatch.setattr(checkpoint, "CHECKPOINT_PATH", path)
    checkpoint.mark("/repo", date(2026, 1, 15), status="generated")
    assert path.exists()
    checkpoint.clear()
    assert not path.exists()
