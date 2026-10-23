import subprocess
from datetime import date, timedelta

_UNIT_SEP = "\x1f"
_RECORD_SEP = "\x1e"


def _resolve_author_email(repo_root: str) -> str | None:
    """`git config user.email` already resolves local -> global -> system,
    so no separate fallback logic is needed here."""
    try:
        out = subprocess.run(
            ["git", "-C", repo_root, "config", "user.email"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except subprocess.CalledProcessError:
        return None


def commits_for_day(repo_root: str, day: date) -> list[dict]:
    email = _resolve_author_email(repo_root)
    since = f"{day.isoformat()} 00:00:00"
    until = f"{(day + timedelta(days=1)).isoformat()} 00:00:00"

    cmd = [
        "git", "-C", repo_root, "log", "--all",
        "--since", since, "--until", until, "--date=iso-local",
        f"--pretty=format:%H{_UNIT_SEP}%ad{_UNIT_SEP}%s{_UNIT_SEP}%b{_RECORD_SEP}",
    ]
    if email:
        cmd[4:4] = ["--author", email]

    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return []

    commits: list[dict] = []
    seen: set[str] = set()
    for record in out.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split(_UNIT_SEP)
        if len(parts) != 4:
            continue
        commit_hash, commit_date, subject, body = parts
        if commit_hash in seen:
            continue
        seen.add(commit_hash)
        commits.append({
            "hash": commit_hash,
            "date": commit_date,
            "subject": subject,
            "body": body,
        })
    return commits
