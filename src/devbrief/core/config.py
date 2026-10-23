from pathlib import Path

STATE_DIR = Path.home() / ".devbrief"
LOG_PATH = STATE_DIR / "devbrief.log"
CHECKPOINT_PATH = STATE_DIR / "checkpoint.json"
PROMPT_PATH = STATE_DIR / "prompt_override.txt"
SOURCES_PATH = STATE_DIR / "sources.json"

RETENTION_DAYS = 180
