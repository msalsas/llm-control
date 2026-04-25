"""Switch state management for the 'switch' command."""

import json
import os

_SWITCH_STATE_FILE = os.path.join("/tmp", "llm-switch-state.json")


def save_switch_state(instance_ids: list[str]) -> None:
    """Save current LMStudio loaded model instance IDs to temp file."""
    with open(_SWITCH_STATE_FILE, 'w') as f:
        json.dump({"instance_ids": instance_ids}, f)


def load_switch_state() -> list[str]:
    """Load saved state from temp file. Returns empty list if no state exists."""
    if not os.path.exists(_SWITCH_STATE_FILE):
        return []
    with open(_SWITCH_STATE_FILE, 'r') as f:
        data = json.load(f)
    return data.get("instance_ids", [])


def cleanup_switch_state() -> None:
    """Remove temp state file."""
    if os.path.exists(_SWITCH_STATE_FILE):
        os.remove(_SWITCH_STATE_FILE)
