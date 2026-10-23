import json
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"


def _find_cwd(jsonl_files: list[Path]) -> str | None:
    """Scans transcript files in order until a line carries a 'cwd' field."""
    for f in jsonl_files:
        try:
            with f.open() as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        d = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    cwd = d.get("cwd")
                    if cwd:
                        return cwd
        except OSError:
            continue
    return None


def nearest_git_root(path: Path) -> Path | None:
    """Walks up from `path` looking for a `.git` entry (file or directory —
    a git worktree checkout has `.git` as a file, not a directory)."""
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def discover_projects() -> dict[str, list[Path]]:
    """Returns {repo_root_path_str: [jsonl_file, ...]} for every git repo that
    has Claude Code session history, merging sanitized-cwd folders that
    resolve to the same repo root."""
    mapping: dict[str, list[Path]] = {}
    if not PROJECTS_DIR.is_dir():
        return mapping

    for folder in PROJECTS_DIR.iterdir():
        if not folder.is_dir():
            continue
        jsonl_files = sorted(folder.glob("*.jsonl"))
        if not jsonl_files:
            continue
        cwd = _find_cwd(jsonl_files)
        if cwd is None:
            continue
        repo_root = nearest_git_root(Path(cwd))
        if repo_root is None:
            continue
        mapping.setdefault(str(repo_root), []).extend(jsonl_files)

    return mapping
