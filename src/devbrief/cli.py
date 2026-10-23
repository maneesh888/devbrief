import argparse
import sys
from datetime import date

from devbrief.core import log_writer, pipeline, source_config, summarizer


def _cmd_generate(args) -> int:
    day = date.fromisoformat(args.date) if args.date else pipeline.today_local()
    try:
        results = pipeline.run_daily(day=day, project=args.project or None)
    except Exception as e:
        print(f"devbrief: orchestration failed: {e}", file=sys.stderr)
        return 1
    for r in results:
        print(f"{r['repo_root']}: {r['status']}")
    # Per-project failures (status == "error") are captured in the checkpoint
    # and auto-retried next run; they don't fail the process, so one bad repo
    # never blocks launchd from considering the whole job successful.
    return 0


def _cmd_log(args) -> int:
    since = date.fromisoformat(args.since) if args.since else None
    entries = log_writer.read_filtered(project=args.project or None, since=since, limit=args.limit)
    if not entries:
        print("(no entries)")
        return 0
    for e in entries:
        print(f"=== {e.entry_date.isoformat()} | {e.repo_name} | {e.repo_root} ===")
        print(e.text)
        print()
    return 0


def _cmd_projects(args) -> int:
    for repo_root, sources_files in sorted(pipeline.discover_all_sources().items()):
        breakdown = ", ".join(f"{name}: {len(files)}" for name, files in sorted(sources_files.items()))
        print(f"{repo_root}  ({breakdown})")
    return 0


def _cmd_prompt(args) -> int:
    print(summarizer.DEFAULT_SYSTEM_PROMPT)
    return 0


def _cmd_sources_list(args) -> int:
    for name, enabled in sorted(source_config.load().items()):
        print(f"{'[x]' if enabled else '[ ]'} {name}")
    return 0


def _cmd_sources_set(args) -> int:
    try:
        source_config.set_enabled(args.name, args.state == "on")
    except ValueError as e:
        print(f"devbrief: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_clear(args) -> int:
    if not args.yes:
        confirm = input("This wipes devbrief.log and checkpoint.json. Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return 1
    pipeline.clear_all_data()
    print("Cleared.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate dev-work briefs from git + Claude Code history")
    sub = parser.add_subparsers(dest="command", required=True)

    p_generate = sub.add_parser("generate", help="Generate today's (or a given day's) briefs")
    p_generate.add_argument("--date", default="", help="YYYY-MM-DD, defaults to today (local time)")
    p_generate.add_argument("--project", default="", help="Absolute repo path or basename; empty = all discovered projects")
    p_generate.set_defaults(func=_cmd_generate)

    p_log = sub.add_parser("log", help="View recent entries")
    p_log.add_argument("--project", default="")
    p_log.add_argument("--since", default="", help="YYYY-MM-DD")
    p_log.add_argument("--limit", type=int, default=30)
    p_log.set_defaults(func=_cmd_log)

    p_projects = sub.add_parser("projects", help="List tracked projects")
    p_projects.set_defaults(func=_cmd_projects)

    p_prompt = sub.add_parser("prompt", help="Print the built-in default summary prompt")
    p_prompt.set_defaults(func=_cmd_prompt)

    p_sources = sub.add_parser("sources", help="List or toggle which AI tools' sessions to read")
    sources_sub = p_sources.add_subparsers(dest="sources_command", required=True)

    p_sources_list = sources_sub.add_parser("list", help="Show which sources are enabled")
    p_sources_list.set_defaults(func=_cmd_sources_list)

    p_sources_set = sources_sub.add_parser("set", help="Enable or disable a source")
    p_sources_set.add_argument("name", choices=sorted(source_config.DEFAULT_SOURCES))
    p_sources_set.add_argument("state", choices=["on", "off"])
    p_sources_set.set_defaults(func=_cmd_sources_set)

    p_clear = sub.add_parser("clear", help="Wipe the log and checkpoint state")
    p_clear.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    p_clear.set_defaults(func=_cmd_clear)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
