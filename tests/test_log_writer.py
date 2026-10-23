from datetime import date, timedelta

from devbrief.core import log_writer


def _patch_log_path(monkeypatch, tmp_path):
    monkeypatch.setattr(log_writer, "LOG_PATH", tmp_path / "devbrief.log")


def test_append_prepends_newest_entry_at_top(monkeypatch, tmp_path):
    _patch_log_path(monkeypatch, tmp_path)
    log_writer.append("/fake/repo", date(2026, 1, 15), "first day")
    log_writer.append("/fake/repo", date(2026, 1, 16), "second day")

    content = log_writer.LOG_PATH.read_text()
    assert content.index("second day") < content.index("first day")


def test_append_order_reflects_most_recently_written_even_same_day(monkeypatch, tmp_path):
    _patch_log_path(monkeypatch, tmp_path)
    log_writer.append("/fake/repo-a", date(2026, 1, 15), "repo a brief")
    log_writer.append("/fake/repo-b", date(2026, 1, 15), "repo b brief")

    content = log_writer.LOG_PATH.read_text()
    assert content.index("repo b brief") < content.index("repo a brief")


def test_read_all_entries_still_readable_regardless_of_order(monkeypatch, tmp_path):
    _patch_log_path(monkeypatch, tmp_path)
    log_writer.append("/fake/repo", date(2026, 1, 15), "first day")
    log_writer.append("/fake/repo", date(2026, 1, 16), "second day")

    entries = log_writer.read_all()
    texts = {e.entry_date: e.text for e in entries}
    assert texts == {date(2026, 1, 15): "first day", date(2026, 1, 16): "second day"}


def test_prune_keeps_newest_first_order(monkeypatch, tmp_path):
    _patch_log_path(monkeypatch, tmp_path)
    today = date.today()
    old_day = today - timedelta(days=200)
    recent_day = today - timedelta(days=1)
    log_writer.append("/fake/repo", old_day, "ancient entry")
    log_writer.append("/fake/repo", recent_day, "recent entry")

    removed = log_writer.prune_older_than(retention_days=180)
    assert removed == 1

    content = log_writer.LOG_PATH.read_text()
    assert "recent entry" in content
    assert "ancient entry" not in content
