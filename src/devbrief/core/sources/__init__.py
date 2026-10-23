from . import claude_code, codex, copilot

REGISTRY = {
    claude_code.NAME: claude_code,
    codex.NAME: codex,
    copilot.NAME: copilot,
}
