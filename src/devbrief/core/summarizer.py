import getpass
import os
import shutil
import subprocess
from pathlib import Path

from . import config

MODEL = "haiku"
MAX_MESSAGES = 40
MAX_MESSAGE_CHARS = 300
TIMEOUT_SECONDS = 60
NO_WORK_MARKER = "NO_WORK"

DEFAULT_SYSTEM_PROMPT = (
    "Write timesheet Description entries for one day of work on one project, using "
    "the commits and session notes given. Describe only what they show. The date "
    "heading is added separately, so do not write one.\n\n"
    "Format:\n"
    "- About six lines, each starting with '- ' (no numbers). Use fewer when the "
    "evidence is thin; merge near-duplicates rather than padding.\n"
    "- Each line is one short sentence that can stand alone as a record "
    "Description, so the day can be split into morning and evening sessions.\n"
    "- Cover what was built, tested, verified or reviewed, including testing of "
    "backend APIs where that happened.\n\n"
    "Style rules:\n"
    "- Explain the work only. Write positive, factual statements in past tense.\n"
    "- No negative or filler statements such as 'nothing else was done', 'no "
    "changes finished', 'not completed', and no blockers.\n"
    "- Don't mention AI tools, agents, assistants, prompts, skills or workflows built "
    "around them. If a commit is about such tooling, describe it as development "
    "process or tooling improvements. Don't add verification steps the commits or "
    "session notes don't show.\n"
    "- The session notes are the developer's own chat messages. Use them only as "
    "evidence of work actually carried out. Questions, requests for information, "
    "comparisons, explanations and plans are not work done; leave them out.\n"
    "- Output only the lines, with no headline, heading or closing summary.\n"
    "- If the evidence shows no concrete work carried out, output exactly "
    f"{NO_WORK_MARKER} and nothing else, with no explanation."
)


def _load_system_prompt() -> str:
    """The menu-bar app lets the user override the prompt by writing to
    config.PROMPT_PATH. Fall back to the built-in default if that file is
    missing or empty."""
    try:
        override = config.PROMPT_PATH.read_text().strip()
    except FileNotFoundError:
        return DEFAULT_SYSTEM_PROMPT
    return override or DEFAULT_SYSTEM_PROMPT


def _resolve_claude_bin() -> str:
    """launchd jobs don't inherit the shell PATH, so `claude` may not be
    found via PATH lookup alone — fall back to this machine's known
    install location (`~/.local/bin/claude`)."""
    return (
        os.environ.get("DEVBRIEF_CLAUDE_BIN")
        or shutil.which("claude")
        or str(Path.home() / ".local" / "bin" / "claude")
    )


def _build_env() -> dict:
    """`claude` reports "Not logged in" if $USER is missing — even with a
    valid stored login — and launchd jobs aren't guaranteed to set it. Fill
    in USER/LOGNAME/HOME explicitly rather than trusting the ambient env."""
    env = os.environ.copy()
    user = env.get("USER") or getpass.getuser()
    env["USER"] = user
    env.setdefault("LOGNAME", user)
    env.setdefault("HOME", str(Path.home()))
    return env


def summarize(repo_name: str, commits: list[dict], messages: list[dict], branch: str | None = None) -> str:
    """Shells out to the `claude` CLI in headless mode to write the brief.
    Returns "" when the model finds no concrete work to report.
    Uses the caller's existing Claude Code login (no ANTHROPIC_API_KEY needed,
    as long as the process environment doesn't set one)."""
    commit_lines = "\n".join(f"- {c['subject']}" for c in commits) or "(no commits)"
    msg_lines = "\n".join(
        f"- {m['text'][:MAX_MESSAGE_CHARS]}" for m in messages[:MAX_MESSAGES]
    ) or "(no recorded messages)"
    branch_line = f"Branch: {branch}\n\n" if branch else ""

    prompt = (
        f"{_load_system_prompt()}\n\n"
        f"Project: {repo_name}\n\n"
        f"{branch_line}"
        f"Commits:\n{commit_lines}\n\n"
        f"Session notes (developer chat messages, background evidence only):\n{msg_lines}"
    )

    result = subprocess.run(
        [_resolve_claude_bin(), "-p", prompt, "--model", MODEL, "--output-format", "text"],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
        cwd=str(Path.home()),  # neutral cwd: avoids picking up any particular project's CLAUDE.md/MCP config
        env=_build_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr.strip()}")
    text = result.stdout.strip()
    return "" if text == NO_WORK_MARKER else text
