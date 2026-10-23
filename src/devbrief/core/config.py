from pathlib import Path

STATE_DIR = Path.home() / ".devbrief"
LOG_PATH = STATE_DIR / "devbrief.log"
CHECKPOINT_PATH = STATE_DIR / "checkpoint.json"

RETENTION_DAYS = 180
