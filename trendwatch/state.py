"""Persist what we saw last run so we can detect *new* trends across stateless CI runs.

GitHub Actions runners are ephemeral, so the workflow commits this JSON back to
the repo after each run. That's the same trick TrendRadar uses to diff runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_PATH = Path("state/state.json")


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"feeds": {}, "breakouts": {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
