from datetime import date, datetime
from pathlib import Path

from devbrief.core import checkpoint, discovery, gitlog, log_writer, transcripts
from devbrief.core.config import RETENTION_DAYS
from devbrief.core.summarizer import summarize


def today_local() -> date:
    return datetime.now().astimezone().date()


def _resolve_projects(project: str | None) -> dict[str, list[Path]]:
    projects = discovery.discover_projects()
    if project:
        projects = {
            root: files for root, files in projects.items()
            if project in (root, Path(root).name)
        }
    return projects


def generate_brief_for_project(repo_root: str, day: date, jsonl_files: list[Path] | None = None) -> dict:
    if checkpoint.is_processed(repo_root, day):
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "already_processed"}

    if jsonl_files is None:
        jsonl_files = discovery.discover_projects().get(repo_root, [])

    commits = gitlog.commits_for_day(repo_root, day)
    messages = transcripts.extract_day_text(jsonl_files, day)

    if not commits and not messages:
        checkpoint.mark(repo_root, day, status="skipped_no_activity")
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "skipped_no_activity"}

    repo_name = Path(repo_root).name
    branch = transcripts.dominant_branch(jsonl_files, day)
    try:
        text = summarize(repo_name, commits, messages, branch=branch)
    except Exception as e:
        checkpoint.mark(repo_root, day, status="error", error=str(e))
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "error", "error": str(e)}

    log_writer.append(repo_root, day, text)
    checkpoint.mark(repo_root, day, status="generated", commit_count=len(commits), message_count=len(messages))
    log_writer.prune_older_than(RETENTION_DAYS)
    return {
        "repo_root": repo_root, "date": day.isoformat(), "status": "generated",
        "commit_count": len(commits), "message_count": len(messages), "text": text,
    }


def run_daily(day: date | None = None, project: str | None = None) -> list[dict]:
    day = day or today_local()
    return [
        generate_brief_for_project(repo_root, day, jsonl_files)
        for repo_root, jsonl_files in _resolve_projects(project).items()
    ]


def clear_all_data() -> None:
    log_writer.clear_all()
    checkpoint.clear()
