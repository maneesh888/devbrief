from datetime import date, datetime
from pathlib import Path

from devbrief.core import checkpoint, gitlog, log_writer, source_config
from devbrief.core.config import RETENTION_DAYS
from devbrief.core.sources import REGISTRY
from devbrief.core.summarizer import summarize


def today_local() -> date:
    return datetime.now().astimezone().date()


def discover_all_sources() -> dict[str, dict[str, list[Path]]]:
    """Returns {repo_root: {source_name: [files]}} merged across every
    *enabled* source (devbrief.core.source_config)."""
    combined: dict[str, dict[str, list[Path]]] = {}
    for name in source_config.enabled_names():
        module = REGISTRY[name]
        for repo_root, files in module.discover_projects().items():
            combined.setdefault(repo_root, {})[name] = files
    return combined


def _resolve_projects(project: str | None) -> dict[str, dict[str, list[Path]]]:
    projects = discover_all_sources()
    if project:
        projects = {
            root: sources_files for root, sources_files in projects.items()
            if project in (root, Path(root).name)
        }
    return projects


def _gather_evidence(
    repo_root: str, day: date, sources_files: dict[str, list[Path]] | None
) -> tuple[list[dict], list[dict], str | None]:
    """Shared by generate and preview: commits, merged+sorted messages across
    every source that has files for this repo, and the dominant branch."""
    if sources_files is None:
        sources_files = discover_all_sources().get(repo_root, {})

    commits = gitlog.commits_for_day(repo_root, day)

    messages: list[dict] = []
    branch: str | None = None
    for name, files in sources_files.items():
        module = REGISTRY[name]
        messages.extend(module.extract_day_text(files, day))
        if branch is None and hasattr(module, "dominant_branch"):
            branch = module.dominant_branch(files, day)
    messages.sort(key=lambda e: e["time"])

    return commits, messages, branch


def generate_brief_for_project(
    repo_root: str, day: date, sources_files: dict[str, list[Path]] | None = None
) -> dict:
    if checkpoint.is_processed(repo_root, day):
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "already_processed"}

    commits, messages, branch = _gather_evidence(repo_root, day, sources_files)

    if not commits and not messages:
        checkpoint.mark(repo_root, day, status="skipped_no_activity")
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "skipped_no_activity"}

    repo_name = Path(repo_root).name
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


def preview_brief_for_project(
    repo_root: str, day: date, sources_files: dict[str, list[Path]] | None = None
) -> dict:
    """Like generate_brief_for_project, but never reads or writes the
    checkpoint and never appends to the log — a pure dry run."""
    commits, messages, branch = _gather_evidence(repo_root, day, sources_files)

    if not commits and not messages:
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "skipped_no_activity"}

    repo_name = Path(repo_root).name
    try:
        text = summarize(repo_name, commits, messages, branch=branch)
    except Exception as e:
        return {"repo_root": repo_root, "date": day.isoformat(), "status": "error", "error": str(e)}

    return {
        "repo_root": repo_root, "date": day.isoformat(), "status": "previewed",
        "commit_count": len(commits), "message_count": len(messages), "text": text,
    }


def run_daily(day: date | None = None, project: str | None = None) -> list[dict]:
    day = day or today_local()
    return [
        generate_brief_for_project(repo_root, day, sources_files)
        for repo_root, sources_files in _resolve_projects(project).items()
    ]


def preview_daily(day: date | None = None, project: str | None = None) -> list[dict]:
    day = day or today_local()
    return [
        preview_brief_for_project(repo_root, day, sources_files)
        for repo_root, sources_files in _resolve_projects(project).items()
    ]


def clear_all_data() -> None:
    log_writer.clear_all()
    checkpoint.clear()
