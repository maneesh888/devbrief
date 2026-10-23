import subprocess

from devbrief.core import summarizer


def test_summarize_builds_prompt_and_invokes_claude_cli(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="Worked on X today.\n", stderr="")

    monkeypatch.setattr(summarizer.subprocess, "run", fake_run)
    monkeypatch.setattr(summarizer, "_resolve_claude_bin", lambda: "/fake/bin/claude")

    text = summarizer.summarize("my-repo", [{"subject": "did a thing"}], [{"text": "worked on X"}])

    assert text == "Worked on X today."
    cmd = captured["cmd"]
    assert cmd[0] == "/fake/bin/claude"
    assert "-p" in cmd
    prompt = cmd[cmd.index("-p") + 1]
    assert "my-repo" in prompt
    assert "did a thing" in prompt
    assert "worked on X" in prompt


def test_summarize_includes_branch_when_given(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(summarizer.subprocess, "run", fake_run)
    monkeypatch.setattr(summarizer, "_resolve_claude_bin", lambda: "/fake/bin/claude")

    summarizer.summarize("my-repo", [], [], branch="feature/agentic_workflow")

    prompt = captured["cmd"][captured["cmd"].index("-p") + 1]
    assert "feature/agentic_workflow" in prompt


def test_summarize_omits_branch_line_when_none(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(summarizer.subprocess, "run", fake_run)
    monkeypatch.setattr(summarizer, "_resolve_claude_bin", lambda: "/fake/bin/claude")

    summarizer.summarize("my-repo", [], [])

    prompt = captured["cmd"][captured["cmd"].index("-p") + 1]
    assert "Branch:" not in prompt


def test_summarize_raises_with_stderr_on_nonzero_exit(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Not logged in")

    monkeypatch.setattr(summarizer.subprocess, "run", fake_run)
    monkeypatch.setattr(summarizer, "_resolve_claude_bin", lambda: "/fake/bin/claude")

    try:
        summarizer.summarize("my-repo", [], [])
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "Not logged in" in str(e)


def test_summarize_propagates_unexpected_subprocess_errors(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("claude binary not found")

    monkeypatch.setattr(summarizer.subprocess, "run", fake_run)
    monkeypatch.setattr(summarizer, "_resolve_claude_bin", lambda: "/fake/bin/claude")

    try:
        summarizer.summarize("my-repo", [], [])
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_resolve_claude_bin_prefers_env_override(monkeypatch):
    monkeypatch.setenv("DEVBRIEF_CLAUDE_BIN", "/custom/claude")
    assert summarizer._resolve_claude_bin() == "/custom/claude"


def test_resolve_claude_bin_falls_back_to_path_lookup(monkeypatch):
    monkeypatch.delenv("DEVBRIEF_CLAUDE_BIN", raising=False)
    monkeypatch.setattr(summarizer.shutil, "which", lambda name: "/usr/local/bin/claude")
    assert summarizer._resolve_claude_bin() == "/usr/local/bin/claude"


def test_build_env_fills_in_missing_user(monkeypatch):
    monkeypatch.delenv("USER", raising=False)
    monkeypatch.delenv("LOGNAME", raising=False)
    monkeypatch.setattr(summarizer.getpass, "getuser", lambda: "fakeuser")

    env = summarizer._build_env()
    assert env["USER"] == "fakeuser"
    assert env["LOGNAME"] == "fakeuser"


def test_summarize_passes_env_with_user_to_subprocess(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(summarizer.subprocess, "run", fake_run)
    monkeypatch.setattr(summarizer, "_resolve_claude_bin", lambda: "/fake/bin/claude")

    summarizer.summarize("my-repo", [], [])
    assert captured["env"] is not None
    assert captured["env"].get("USER")
