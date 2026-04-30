#!/usr/bin/env python3
"""Track the active Cortex session for resume across Claude Code turns.

Every `cortex --input-format stream-json` invocation emits a session_id in its
init event. Persisting that id lets follow-up turns run `cortex --resume <id>`
so Cortex sees prior conversation -- real multi-turn instead of one-shot
batches per prompt.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional


STATE_DIR = Path.home() / ".cache" / "cortex-router"
STATE_FILE_NAME = "active-session.json"
STALE_AFTER_SECONDS = 30 * 60


def _state_path() -> Path:
    return STATE_DIR / STATE_FILE_NAME


def load_active_session() -> Optional[dict]:
    """Return the persisted active session dict, or None if missing/stale."""
    path = _state_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if time.time() - data.get("timestamp", 0) > STALE_AFTER_SECONDS:
        return None

    if not data.get("session_id"):
        return None

    return data


def save_active_session(session_id: str) -> None:
    """Persist the session id so subsequent turns can resume."""
    if not session_id:
        return

    payload = {"session_id": session_id, "timestamp": time.time()}
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".active-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def clear_active_session() -> None:
    path = _state_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
