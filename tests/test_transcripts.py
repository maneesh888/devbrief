import json
from datetime import date

from devbrief.core import transcripts


def test_extract_day_text_picks_matching_day(tmp_path, user_line_factory):
    f = tmp_path / "session.jsonl"
    lines = [
        user_line_factory("worked on feature A", "2026-01-15T10:00:00Z", uuid="u1"),
        user_line_factory("other day message", "2026-01-16T10:00:00Z", uuid="u2"),
    ]
    f.write_text("\n".join(json.dumps(l) for l in lines) + "\n")

    entries = transcripts.extract_day_text([f], date(2026, 1, 15))
    assert len(entries) == 1
    assert entries[0]["text"] == "worked on feature A"


def test_extract_day_text_skips_plain_string_content(tmp_path):
    f = tmp_path / "session.jsonl"
    line = {
        "type": "user", "isMeta": False, "uuid": "u1",
        "timestamp": "2026-01-15T10:00:00Z",
        "message": {"role": "user", "content": "/clear"},
    }
    f.write_text(json.dumps(line) + "\n")
    assert transcripts.extract_day_text([f], date(2026, 1, 15)) == []


def test_extract_day_text_skips_interruption_markers(tmp_path, user_line_factory):
    f = tmp_path / "session.jsonl"
    line = user_line_factory("[Request interrupted by user for tool use]", "2026-01-15T10:00:00Z")
    f.write_text(json.dumps(line) + "\n")
    assert transcripts.extract_day_text([f], date(2026, 1, 15)) == []


def test_extract_day_text_skips_meta_lines(tmp_path, user_line_factory):
    f = tmp_path / "session.jsonl"
    line = user_line_factory("hidden", "2026-01-15T10:00:00Z", is_meta=True)
    f.write_text(json.dumps(line) + "\n")
    assert transcripts.extract_day_text([f], date(2026, 1, 15)) == []


def test_extract_day_text_dedupes_by_uuid_across_files(tmp_path, user_line_factory):
    line = user_line_factory("same message", "2026-01-15T10:00:00Z", uuid="dup")
    f1 = tmp_path / "s1.jsonl"
    f2 = tmp_path / "s2.jsonl"
    f1.write_text(json.dumps(line) + "\n")
    f2.write_text(json.dumps(line) + "\n")

    entries = transcripts.extract_day_text([f1, f2], date(2026, 1, 15))
    assert len(entries) == 1


def test_extract_day_text_sorted_by_time(tmp_path, user_line_factory):
    f = tmp_path / "session.jsonl"
    lines = [
        user_line_factory("second", "2026-01-15T12:00:00Z", uuid="u2"),
        user_line_factory("first", "2026-01-15T09:00:00Z", uuid="u1"),
    ]
    f.write_text("\n".join(json.dumps(l) for l in lines) + "\n")

    entries = transcripts.extract_day_text([f], date(2026, 1, 15))
    assert [e["text"] for e in entries] == ["first", "second"]


def test_dominant_branch_picks_most_common(tmp_path):
    f = tmp_path / "session.jsonl"
    lines = [
        {"type": "assistant", "timestamp": "2026-01-15T09:00:00Z", "gitBranch": "feature/agentic_workflow"},
        {"type": "user", "timestamp": "2026-01-15T10:00:00Z", "gitBranch": "feature/agentic_workflow"},
        {"type": "assistant", "timestamp": "2026-01-15T11:00:00Z", "gitBranch": "main"},
    ]
    f.write_text("\n".join(json.dumps(l) for l in lines) + "\n")

    assert transcripts.dominant_branch([f], date(2026, 1, 15)) == "feature/agentic_workflow"


def test_dominant_branch_none_when_no_branch_info(tmp_path):
    f = tmp_path / "session.jsonl"
    line = {"type": "user", "timestamp": "2026-01-15T09:00:00Z"}
    f.write_text(json.dumps(line) + "\n")

    assert transcripts.dominant_branch([f], date(2026, 1, 15)) is None


def test_dominant_branch_ignores_other_days(tmp_path):
    f = tmp_path / "session.jsonl"
    line = {"type": "user", "timestamp": "2026-01-16T09:00:00Z", "gitBranch": "main"}
    f.write_text(json.dumps(line) + "\n")

    assert transcripts.dominant_branch([f], date(2026, 1, 15)) is None
