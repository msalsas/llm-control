"""Presentation views for CLI output."""

from llm_control.models.resource import ResourceUsage


def format_resource_table(resources: ResourceUsage) -> str:
    """Format resource usage as a table string."""
    from ..utils.formatter import format_table
    headers = ["Resource", "Value"]
    rows = [
        ["VRAM Used", f"{resources.vram_used:.2f} GB"],
        ["VRAM Total", f"{resources.vram_total:.2f} GB"],
        ["VRAM %", f"{resources.vram_percent:.1f}%"],
        ["RAM Used", f"{resources.ram_used:.2f} GB"],
        ["RAM Total", f"{resources.ram_total:.2f} GB"],
        ["RAM %", f"{resources.ram_percent:.1f}%"],
        ["CPU Usage", f"{resources.cpu_usage:.1f}%"],
        ["GPU Count", str(resources.gpu_count)],
    ]
    return format_table(rows, headers)


def format_loaded_models_table(models: list[dict]) -> str | None:
    """Format loaded models as a table. Returns None if no models."""
    from ..utils.formatter import format_table
    if not models:
        return "No models loaded."
    has_vram = any(m.get("vram_allocated_gb", 0) > 0 for m in models)
    headers = ["Name", "Instance ID"] + (["VRAM (GB)",] if has_vram else [])
    rows = [
        [m["name"], m["instance_id"]] + ([f"{m['vram_allocated_gb']:.2f}",] if has_vram else [])
        for m in models
    ]
    return format_table(rows, headers)


def format_available_models_table(models: list[dict]) -> str | None:
    """Format available/downloaded models as a table."""
    from ..utils.formatter import format_table
    if not models:
        return "No models available."
    has_size = any(m.get("size_gb", 0) > 0 for m in models)
    has_loaded = any(m.get("loaded_instances") for m in models)

    if has_size and has_loaded:
        headers = ["Name", "Path", "Size (GB)", "Loaded Instances"]
        rows = [[m["name"], m["path"], f"{m['size_gb']:.1f}", ", ".join(m.get('loaded_instances', []))] for m in models]
    elif has_size:
        headers = ["Name", "Path", "Size (GB)"]
        rows = [[m["name"], m["path"], f"{m['size_gb']:.1f}"] for m in models]
    else:
        headers = ["Name", "Path"]
        rows = [[m["name"], m["path"]] for m in models]
    return format_table(rows, headers)


def format_status_table(results: dict) -> str:
    """Format backend status results as a table."""
    from ..utils.formatter import format_table
    headers = ["Backend", "Reachable", "Loaded Models"]
    rows = []
    for name, info in results.items():
        reachable = "Yes" if info.get("reachable") else "No"
        loaded = info.get("loaded_models", "-")
        not_running = "not running" if (not info.get("reachable") and "error" not in info) else ""
        extra = f" ({info.get('error', '')})" if info.get("error") else (f" [{not_running}]" if not_running else "")
        rows.append([name.capitalize(), reachable, str(loaded) + extra])
    return format_table(rows, headers)
