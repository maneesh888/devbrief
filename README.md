# devbrief

Generates short, pasteable daily timesheet briefs by correlating git commit
history with Claude Code session transcripts, one brief per (project, day).

## How it works

- **Project discovery**: every Claude Code session transcript under
  `~/.claude/projects/*/*.jsonl` carries a `cwd` field. Any `cwd` whose nearest
  ancestor contains a `.git` entry is treated as a tracked project — no manual
  config list.
- **No API key.** Summarization shells out to the `claude` CLI in headless
  mode (`claude -p ...`), which uses your existing Claude Code login — no
  `ANTHROPIC_API_KEY` to manage, as long as that variable isn't set in the
  process environment (it would take precedence over the stored login if it
  were).
- **Per (project, day)**: pulls that day's git commits (`git log --all
  --since/--until`, filtered to the repo's own `git config user.email`) and
  that day's user-authored transcript text (system-generated markers like
  `[Request interrupted by user for tool use]` are filtered out), then makes
  one `claude -p` call (Haiku) to produce a 2-4 sentence first-person
  paragraph.
- **Output**: appended to `~/.devbrief/devbrief.log` (never rewritten, except
  when pruning). State/idempotency tracked in `~/.devbrief/checkpoint.json`.
- **Automatic trigger**: a `launchd` job (see `launchd/`) runs `devbrief
  generate` daily.

### A `claude` CLI gotcha discovered while building this

`claude --bare -p ...` loses the stored login entirely ("Not logged in ·
Please run /login") in this CLI version, despite docs suggesting `--bare`
only skips project config. `summarizer.py` therefore does **not** pass
`--bare`, and instead runs with `cwd` set to your home directory, which keeps
auth working while still avoiding picking up any particular project's
CLAUDE.md/MCP config.

## Setup

```bash
git clone https://github.com/maneesh888/devbrief.git
cd devbrief
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# put the CLI where the menu-bar app and launchd can find it
mkdir -p ~/.local/bin
ln -sf "$PWD/.venv/bin/devbrief" ~/.local/bin/devbrief
```

`claude` is located via `$DEVBRIEF_CLAUDE_BIN`, then `PATH`, then falling
back to `~/.local/bin/claude`. `launchd` jobs don't inherit your shell's
`PATH`, so if your `claude` binary lives somewhere else, set
`DEVBRIEF_CLAUDE_BIN` in the plist's `EnvironmentVariables`.

### Install the scheduled job (manual, one-time)

```bash
sed "s|__HOME__|$HOME|g" launchd/com.maneesh.devbrief.daily.plist \
  > ~/Library/LaunchAgents/com.maneesh.devbrief.daily.plist
launchctl load ~/Library/LaunchAgents/com.maneesh.devbrief.daily.plist
# to test immediately instead of waiting for 19:00:
launchctl start com.maneesh.devbrief.daily
```

Edit the `Hour`/`Minute` in the plist before installing it if 19:00 local isn't
the right time.

## Menu-bar app (macOS)

`DevBriefMenuBar/` is a native SwiftUI menu-bar app that drives the CLI:
generate a date range (or preview it without saving), toggle the daily job,
launch at login, per-source tracking, edit the prompt, and browse recent
entries.

Download `DevBriefMenuBar.zip` from the latest GitHub release, unzip, and move
it to `/Applications`. The release is ad-hoc signed, so on first launch
right-click the app and choose **Open** (or run `xattr -dr com.apple.quarantine
/Applications/DevBriefMenuBar.app`). The app expects the CLI at
`~/.local/bin/devbrief` (see Setup) or at `$DEVBRIEF_BIN`.

To build it yourself: open `DevBriefMenuBar/DevBriefMenuBar.xcodeproj` in
Xcode and run the `DevBriefMenuBar` scheme.

## Manual use

```bash
.venv/bin/devbrief generate                       # today, all tracked projects
.venv/bin/devbrief generate --date 2026-10-15 --project my-app
.venv/bin/devbrief log                             # view recent entries
.venv/bin/devbrief log --project my-app --since 2026-10-01
.venv/bin/devbrief projects                        # list tracked projects
.venv/bin/devbrief clear                           # wipe log + checkpoint (asks to confirm)
```

## Tests

```bash
.venv/bin/pytest              # isolated unit + pipeline tests (claude CLI is mocked)
.venv/bin/pytest -m integration   # also reads REAL ~/.claude/projects state
```

Retention: every `generate` run also auto-prunes log entries older than 180
days as a safety net.
