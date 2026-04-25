"""CLI entry point — llm-control command line interface."""

import asyncio
import logging
from typing import Any

import httpx
import click

# Configure root logger
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _validate_interval(ctx, param, value):
    """Validate that interval is at least 1 second."""
    if value < 1:
        raise click.BadParameter("interval must be >= 1")
    return value


def get_settings() -> "Settings":
    """Load settings from environment."""
    from .utils.config import Settings as _Settings
    return _Settings()


async def create_lmstudio_client(settings: Any) -> "LmStudioClient":
    """Create an LMStudio client from settings."""
    from .services.lmstudio.client import LmStudioClient as _LMC
    retry = getattr(settings, "retry_intervals", None)
    return _LMC(
        base_url=settings.lmstudio_base_url,
        token=settings.lmstudio_token,
        retry_intervals=retry,
    )


async def create_swarmui_client(settings: Any) -> "SwarmUIClient":
    """Create a SwarmUI client from settings."""
    from .services.swarmui.client import SwarmUIClient as _SUC
    retry = getattr(settings, "retry_intervals", None)
    return _SUC(
        base_url=settings.swarmui_base_url,
        token=settings.swarmui_token,
        retry_intervals=retry,
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="llm-control")
def cli():
    """llm-control: Monitor and manage LMStudio and SwarmUI backends."""
    pass


@cli.command()
@click.option("--backend", "-b", "backend",
              type=click.Choice(["lmstudio", "swarmui", "all"]),
              default="all", help="Backend to monitor")
@click.option("--watch", "-w", is_flag=True, help="Continuous polling mode")
@click.option("--interval", "-i", type=int, default=30, show_default=True,
              callback=_validate_interval,
              help="Polling interval in seconds (for --watch)")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output results as JSON instead of table format")
@click.option("-q", "--quiet", is_flag=True, default=False,
             help="Suppress messages for unreachable backends")
def monitor(backend: str, watch: bool, interval: int, as_json: bool, quiet: bool):
    """Monitor backend status and resource usage.

    Tracks consecutive failures per backend; warns after 3 consecutive errors.
    """

    async def _do_monitor():
        from .utils.formatter import format_table, format_json
        from .services.lmstudio.monitor import LmStudioMonitor as LSM, LmStudioManager as LSMgr
        from .services.swarmui.monitor import SwarmUIMonitor as SUM, SwarmUIManager as SUMgr

        settings = get_settings()
        backends_to_monitor = []
        if backend == "lmstudio":
            backends_to_monitor.append(("lmstudio", await create_lmstudio_client(settings)))
        elif backend == "swarmui":
            backends_to_monitor.append(("swarmui", await create_swarmui_client(settings)))
        else:
            backends_to_monitor.append(("lmstudio", await create_lmstudio_client(settings)))
            backends_to_monitor.append(("swarmui", await create_swarmui_client(settings)))

        # Track consecutive failures per backend for watch mode alerts
        failure_counts: dict[str, int] = {name: 0 for name, _ in backends_to_monitor}
        WARN_THRESHOLD = 3

        try:
            while True:
                for name, client in backends_to_monitor:
                    try:
                        if name == "lmstudio":
                            mon = LSM(client)
                            mgr = LSMgr(client)
                            lmstudio_data: dict[str, Any] = {"backend": "lmstudio"}

                            try:
                                loaded = await mon.list_loaded_models()
                                lmstudio_data["loaded_models"] = [
                                    {"name": m.name, "instance_id": m.instance_id} for m in loaded
                                ]
                                # Only add VRAM column if backend reports non-zero values
                                if any(m.vram_allocated > 0 for m in loaded):
                                    lmstudio_data["loaded_models"] = [
                                        {"name": m.name, "instance_id": m.instance_id,
                                         "vram_allocated_gb": round(m.vram_allocated, 2)} for m in loaded
                                    ]
                            except NotImplementedError as e:
                                lmstudio_data["loaded_models_error"] = str(e)

                            try:
                                avail = await mgr.list_available_models()
                                lmstudio_data["available_models"] = [
                                    {"name": m.name, "path": m.path} for m in avail
                                ]
                            except NotImplementedError as e:
                                lmstudio_data["available_models_error"] = str(e)

                        elif name == "swarmui":
                            mon = SUM(client)
                            mgr = SUMgr(client)
                            swarmui_data: dict[str, Any] = {"backend": "swarmui"}

                            try:
                                resources = await mon.get_resource_info()
                                swarmui_data["resources"] = {
                                    "vram_used_gb": round(resources.vram_used, 2),
                                    "vram_total_gb": round(resources.vram_total, 2),
                                    "vram_percent": round(resources.vram_percent, 1),
                                    "ram_used_gb": round(resources.ram_used, 2),
                                    "ram_total_gb": round(resources.ram_total, 2),
                                    "ram_percent": round(resources.ram_percent, 1),
                                    "cpu_usage_percent": round(resources.cpu_usage, 1),
                                    "gpu_count": resources.gpu_count,
                                }
                            except NotImplementedError as e:
                                swarmui_data["resources_error"] = str(e)

                            try:
                                loaded = await mon.list_loaded_models()
                                models_list = [
                                    {"name": m.name, "instance_id": m.instance_id} for m in loaded
                                ]
                                # Only add VRAM column if backend reports non-zero values
                                if any(m.vram_allocated > 0 for m in loaded):
                                    models_list = [
                                        {"name": m.name, "instance_id": m.instance_id,
                                         "vram_allocated_gb": round(m.vram_allocated, 2)}
                                        for m in loaded
                                    ]
                                swarmui_data["loaded_models"] = models_list
                            except NotImplementedError as e:
                                swarmui_data["loaded_models_error"] = str(e)

                        # Use the appropriate data dict based on backend name
                        data = lmstudio_data if name == "lmstudio" else swarmui_data


                        if as_json:
                            click.echo(format_json(data))
                        else:
                            click.echo(f"\n=== {data['backend'].upper()} ===")
                            if "resources" in data:
                                headers = ["Resource", "Value"]
                                rows = [
                                    ["VRAM Used", f"{data['resources']['vram_used_gb']} GB"],
                                    ["VRAM Total", f"{data['resources']['vram_total_gb']} GB"],
                                    ["VRAM %", f"{data['resources']['vram_percent']}%"],
                                    ["RAM Used", f"{data['resources']['ram_used_gb']} GB"],
                                    ["RAM Total", f"{data['resources']['ram_total_gb']} GB"],
                                    ["RAM %", f"{data['resources']['ram_percent']}%"],
                                    ["CPU Usage", f"{data['resources']['cpu_usage_percent']}%"],
                                    ["GPU Count", str(data['resources']['gpu_count'])],
                                ]
                                click.echo(format_table(rows, headers))

                            if "loaded_models" in data:
                                if data["loaded_models"]:
                                    has_vram = any("vram_allocated_gb" in m for m in data["loaded_models"])
                                    if has_vram:
                                        headers = ["Name", "Instance ID", "VRAM (GB)"]
                                        rows = [[m["name"], m["instance_id"], f"{m['vram_allocated_gb']:.2f}"] for m in data["loaded_models"]]
                                    else:
                                        headers = ["Name", "Instance ID"]
                                        rows = [[m["name"], m["instance_id"]] for m in data["loaded_models"]]
                                    click.echo(format_table(rows, headers))
                                else:
                                    click.echo("No models loaded.")

                            if "available_models" in data:
                                click.echo()  # blank line separator
                                if data["available_models"]:
                                    headers = ["Name", "Path"]
                                    rows = [[m["name"], m["path"]] for m in data["available_models"]]
                                    click.echo(format_table(rows, headers))

                        # Reset failure count on success
                        failure_counts[name] = 0

                    except Exception as e:
                        failure_counts[name] += 1
                        error_msg = "not running" if any(x in type(e).__name__ for x in ["Connect", "Timeout"]) else str(e)
                        if not quiet or as_json:
                            if as_json:
                                click.echo(format_json({"backend": name, "error": error_msg}))
                            else:
                                click.echo(f"[{name}] {error_msg}", err=True)
                        # Warn after consecutive failures threshold
                        if failure_counts[name] >= WARN_THRESHOLD and not as_json and not quiet:
                            click.echo(
                                f"[WARN] {name} failed {failure_counts[name]} times consecutively",
                                err=True,
                            )

                if not watch:
                    break
                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            click.echo("\nExiting...")
        finally:
            # Close all HTTP clients to prevent resource leaks
            for name, client in backends_to_monitor:
                try:
                    await client.close()
                except Exception:
                    pass

    asyncio.run(_do_monitor())


@cli.command()
@click.option("--backend", "-b", "backend",
              type=click.Choice(["lmstudio", "swarmui", "all"]),
              default="all", help="Backend to query")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output results as JSON")
def models(backend: str, as_json: bool):
    """List available and loaded models."""

    async def _do_models():
        from .utils.formatter import format_table, format_json
        from .services.lmstudio.monitor import LmStudioManager as LSMgr
        from .services.swarmui.monitor import SwarmUIManager as SUMgr

        settings = get_settings()
        targets = [backend] if backend != "all" else ["lmstudio", "swarmui"]
        results: dict[str, Any] = {}

        for target in targets:
            try:
                if target == "lmstudio":
                    async with await create_lmstudio_client(settings) as client:
                        manager = LSMgr(client)
                        avail = await manager.list_available_models()
                        results["lmstudio"] = {
                            "models": [
                                {"name": m.name, "path": m.path, "size_gb": round(m.size_gb, 2),
                                 "loaded_instances": m.loaded_instances}
                                for m in avail
                            ]
                        }
                else:
                    async with await create_swarmui_client(settings) as client:
                        manager = SUMgr(client)
                        avail = await manager.list_available_models()
                        results["swarmui"] = {
                            "models": [
                                {"name": m.name, "path": m.path, "size_gb": round(m.size_gb, 2)}
                                for m in avail
                            ]
                        }
            except Exception as e:
                error_msg = "not running" if any(x in type(e).__name__ for x in ["Connect", "Timeout"]) else str(e)
                results[target] = {"error": error_msg}

        if as_json:
            click.echo(format_json(results))
        else:
            for name, info in results.items():
                click.echo(f"\n=== {name.upper()} ===")
                if "error" in info:
                    click.echo(info["error"])
                elif info.get("models"):
                    headers = ["Name", "Path", "Size (GB)", "Loaded Instances"]
                    rows = [[m["name"], m["path"], f"{m['size_gb']:.1f}", ", ".join(m.get('loaded_instances', []))] for m in info["models"]]
                    click.echo(format_table(rows, headers))
                else:
                    click.echo("No models available.")

    try:
        asyncio.run(_do_models())
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command()
@click.option("--backend", "-b", "backend",
              type=click.Choice(["lmstudio", "swarmui"]),
              default="lmstudio", help="Backend to load model on")
@click.option("--model", "-m", required=True, help="Model path or name to load")
def load(backend: str, model: str):
    """Load a model onto the specified backend."""

    async def _do_load():
        from .services.lmstudio.monitor import LmStudioManager as LSMgr
        from .services.swarmui.monitor import SwarmUIManager as SUMgr

        settings = get_settings()
        if backend == "lmstudio":
            async with await create_lmstudio_client(settings) as client:
                manager = LSMgr(client)
                await manager.load_model(model)
                click.echo(f"Loaded '{model}' on LMStudio.")
        else:
            async with await create_swarmui_client(settings) as client:
                manager = SUMgr(client)
                await manager.load_model(model)
                click.echo(f"Loaded '{model}' on SwarmUI.")

    try:
        asyncio.run(_do_load())
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command()
@click.option("--backend", "-b", "backend",
              type=click.Choice(["lmstudio", "swarmui"]),
              default="lmstudio", help="Backend to unload model from")
@click.option("--model", "-m", required=True, help="Model instance ID or name to unload")
def unload(backend: str, model: str):
    """Unload a specific model instance (LMStudio only)."""

    async def _do_unload():
        from .services.lmstudio.monitor import LmStudioManager as LSMgr

        settings = get_settings()
        if backend == "lmstudio":
            async with await create_lmstudio_client(settings) as client:
                manager = LSMgr(client)
                await manager.unload_model(model)
                click.echo(f"Unloaded instance '{model}' from LMStudio.")
        else:
            raise click.ClickException(
                "SwarmUI doesn't support per-model unload. "
                "Use `free-memory` instead."
            )

    try:
        asyncio.run(_do_unload())
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command()
@click.option("--backend", "-b", "backend",
              type=click.Choice(["lmstudio", "swarmui"]),
              default="lmstudio", help="Backend to free memory on")
def free_memory(backend: str):
    """Free all model memory. LMStudio unloads each loaded model; SwarmUI clears ALL."""

    async def _do_free():
        from .services.lmstudio.monitor import LmStudioManager as LSMgr
        from .services.swarmui.monitor import SwarmUIManager as SUMgr

        settings = get_settings()
        if backend == "lmstudio":
            async with await create_lmstudio_client(settings) as client:
                manager = LSMgr(client)
                await manager.free_memory()
                click.echo("LMStudio: Freed all model memory.")
        else:
            async with await create_swarmui_client(settings) as client:
                manager = SUMgr(client)
                await manager.free_memory()
                click.echo("SwarmUI: Cleared all backend memory.")

    try:
        asyncio.run(_do_free())
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command()
@click.option("--backend", "-b", "backend",
              type=click.Choice(["lmstudio", "swarmui"]),
              default=None, help="Check only this backend (default: all)")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output results as JSON")
def status(backend: str | None, as_json: bool):
    """Quick health check of backends. Use --backend to filter."""

    async def _do_status():
        from .utils.formatter import format_table, format_json
        from .services.lmstudio.monitor import LmStudioMonitor as LSM
        from .services.swarmui.monitor import SwarmUIMonitor as SUM

        settings = get_settings()
        results: dict[str, Any] = {}

        # Determine which backends to check
        if backend is not None:
            targets = [backend]
        else:
            targets = ["lmstudio", "swarmui"]

        for target in targets:
            try:
                if target == "lmstudio":
                    async with await create_lmstudio_client(settings) as client:
                        mon = LSM(client)
                        try:
                            loaded = await mon.list_loaded_models()
                            results["lmstudio"] = {"reachable": True, "loaded_models": len(loaded)}
                        except Exception as e:
                            results["lmstudio"] = {"reachable": False, "error": str(e)}
                else:
                    async with await create_swarmui_client(settings) as client:
                        mon = SUM(client)
                        try:
                            loaded = await mon.list_loaded_models()
                            results["swarmui"] = {"reachable": True, "loaded_models": len(loaded)}
                        except Exception as e:
                            results["swarmui"] = {"reachable": False, "error": str(e)}
            except Exception as e:
                results[target] = {"reachable": False, "error": str(e)}

        if as_json:
            click.echo(format_json(results))
        else:
            headers = ["Backend", "Reachable", "Loaded Models"]
            rows = []
            for name, info in results.items():
                reachable = "Yes" if info.get("reachable") else "No"
                loaded = info.get("loaded_models", "-")
                not_running = "not running" if (not info.get("reachable") and "error" not in info) else ""
                extra = f" ({info.get('error', '')})" if info.get("error") else (f" [{not_running}]" if not_running else "")
                rows.append([name.capitalize(), reachable, str(loaded) + extra])
            click.echo(format_table(rows, headers))

    try:
        asyncio.run(_do_status())
    except Exception as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
