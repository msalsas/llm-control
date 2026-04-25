"""Output formatting utilities."""

import json
from typing import Any


def format_table(rows: list[list[str]], headers: list[str]) -> str:
    """Format data as a human-readable table.

    Args:
        rows: List of row lists (each row is a list of string values).
        headers: Column header names.

    Returns:
        Formatted table string.
    """
    if not headers:
        return ""

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    # Build header row
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    separator = " | ".join("-" * w for w in widths)

    # Build body
    lines = [header_line, separator]
    for row in rows:
        line = " | ".join(
            str(cell).ljust(widths[i]) if i < len(widths) else str(cell)
            for i, cell in enumerate(row)
        )
        lines.append(line)

    return "\n".join(lines)


def format_json(data: Any) -> str:
    """Format data as pretty-printed JSON.

    Args:
        data: Any serializable Python object.

    Returns:
        Formatted JSON string.
    """
    return json.dumps(data, indent=2, default=str)


def parse_model_list(data: list[dict] | dict) -> list[dict]:
    """Shared utility to extract model entries from API responses.

    Handles various response formats with fallback keys:
    - Top-level list of models
    - Dict with 'models', 'loaded_models', or 'available' key containing a list

    Args:
        data: Raw API response (list or dict).

    Returns:
        List of model entry dicts.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("models", "loaded_models", "available_models", "downloaded"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []
