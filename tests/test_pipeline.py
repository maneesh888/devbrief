from datetime import date

from devbrief.core import checkpoint, log_writer, pipeline


def _patch_state(monkeypatch, tmp_path):
    monkeypatch.setattr(checkpoint, "CHECKPOINT_PATH", tmp_path / "checkpoint.json")
    monkeypatch.setattr(log_writer, "LOG_PATH", tmp_path / "devbrief.log")


def test_skips_when_no_activity(monkeypatch, tmp_path):
    _patch_state(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline.gitlog, "commits_for_day", lambda repo, day: [])
    monkeypatch.setattr(pipeline.transcripts, "extract_day_text", lambda files, day: [])

    result = pipeline.generate_brief_for_project("/fake/repo", date(2026, 1, 15), jsonl_files=[])
    assert result["status"] == "skipped_no_activity"
    assert checkpoint.is_processed("/fake/repo", date(2026, 1, 15)) is True


def test_marks_error_on_summarize_failure_and_allows_retry(monkeypatch, tmp_path):
    _patch_state(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline.gitlog, "commits_for_day", lambda repo, day: [{"subject": "did a thing"}])
    monkeypatch.setattr(pipeline.transcripts, "extract_day_text", lambda files, day: [])

    def boom(repo_name, commits, messages, branch=None):
        raise RuntimeError("claude CLI not found")

    monkeypatch.setattr(pipeline, "summarize", boom)

    result = pipeline.generate_brief_for_project("/fake/repo", date(2026, 1, 15), jsonl_files=[])
    assert result["status"] == "error"
    # Not "done" -> should retry next time.
    assert checkpoint.is_processed("/fake/repo", date(2026, 1, 15)) is False


def test_generates_and_writes_log(monkeypatch, tmp_path):
    _patch_state(monkeypatch, tmp_path)
    today = pipeline.today_local()
    monkeypatch.setattr(pipeline.gitlog, "commits_for_day", lambda repo, day: [{"subject": "did a thing"}])
    monkeypatch.setattr(pipeline.transcripts, "extract_day_text", lambda files, day: [{"text": "worked on X", "time": None}])
    monkeypatch.setattr(pipeline, "summarize", lambda repo_name, commits, messages, branch=None: "Worked on X today.")

    result = pipeline.generate_brief_for_project("/fake/repo", today, jsonl_files=[])
    assert result["status"] == "generated"
    assert checkpoint.is_processed("/fake/repo", today) is True

    entries = log_writer.read_all()
    assert len(entries) == 1
    assert entries[0].text == "Worked on X today."


def test_already_processed_short_circuits(monkeypatch, tmp_path):
    _patch_state(monkeypatch, tmp_path)
    checkpoint.mark("/fake/repo", date(2026, 1, 15), status="generated")

    called = {"gitlog": False}

    def fail_if_called(*args, **kwargs):
        called["gitlog"] = True
        raise AssertionError("should not be called when already processed")

    monkeypatch.setattr(pipeline.gitlog, "commits_for_day", fail_if_called)

    result = pipeline.generate_brief_for_project("/fake/repo", date(2026, 1, 15), jsonl_files=[])
    assert result["status"] == "already_processed"
    assert called["gitlog"] is False


def test_run_daily_filters_by_project(monkeypatch, tmp_path):
    _patch_state(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline.discovery, "discover_projects", lambda: {"/fake/repo-a": [], "/fake/repo-b": []})
    monkeypatch.setattr(pipeline.gitlog, "commits_for_day", lambda repo, day: [])
    monkeypatch.setattr(pipeline.transcripts, "extract_day_text", lambda files, day: [])

    results = pipeline.run_daily(day=date(2026, 1, 15), project="repo-a")
    assert [r["repo_root"] for r in results] == ["/fake/repo-a"]


def test_clear_all_data_removes_log_and_checkpoint(monkeypatch, tmp_path):
    _patch_state(monkeypatch, tmp_path)
    checkpoint.mark("/fake/repo", date(2026, 1, 15), status="generated")
    log_writer.append("/fake/repo", date(2026, 1, 15), "some brief")

    pipeline.clear_all_data()

    assert checkpoint.all_entries() == {}
    assert log_writer.read_all() == []
