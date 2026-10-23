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

DEFAULT_SYSTEM_PROMPT = (
    "You write a daily status update about one project, for a non-technical senior "
    "manager audience — someone who doesn't read code and doesn't know internal tool "
    "names, acronyms or jargon (e.g. 'S1-S4 severity labels', 'hooks', 'CI pipeline', "
    "'pbxproj'). Translate every technical detail into plain business language: what "
    "capability or risk it addresses, not what file or flag changed.\n\n"
    "Structure your answer in exactly this format:\n"
    "Headline: <one plain-English sentence naming the overall initiative this work "
    "belongs to — use the branch name as a hint if it's informative (e.g. a branch "
    "called 'feature/agentic_workflow' is about building an AI-agent-assisted "
    "development process), but never invent an initiative name the evidence doesn't "
    "support>\n"
    "- <bullet 1: a concrete thing accomplished, in plain language>\n"
    "- <bullet 2>\n"
    "- <bullet 3, optional, omit if there isn't a genuinely distinct third point>\n"
    "Why it matters: <one sentence on the business value or risk this reduces>\n\n"
    "Use ONLY the evidence given (commits, session notes, branch name). Never invent "
    "specifics. If evidence is thin or purely exploratory, say so plainly in the "
    "bullets rather than padding with invented detail."
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
        f"Notes/requests during the day:\n{msg_lines}"
    )

    result = subprocess.run(
        [_resolve_claude_bin(), "-p", prompt, "--model", MODEL, "--output-format", "text"],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
        cwd=str(Path.home()),  # neutral cwd: avoids picking up any particular project's CLAUDE.md/MCP config
        env=_build_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout.strip()
