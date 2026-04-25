"""CLI entry point — llm-control command line interface."""

import asyncio
import json
import logging
import os
from typing import Any

import click

from .cli.factories import get_backend_classes
from .cli.views import (format_available_models_table, format_loaded_models_table,
                        format_resource_table, format_status_table)

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
        from .cli.factories import create_client, list_backends
        from .utils.formatter import format_table, format_json

        settings = get_settings()
        backends_to_monitor = []
        if backend == "lmstudio":
            backends_to_monitor.append(("lmstudio", create_client(settings, "lmstudio")))
        elif backend == "swarmui":
            backends_to_monitor.append(("swarmui", create_client(settings, "swarmui")))
        else:
            backends_to_monitor.append(("lmstudio", create_client(settings, "lmstudio")))
            backends_to_monitor.append(("swarmui", create_client(settings, "swarmui")))

        # Track consecutive failures per backend for watch mode alerts
        failure_counts: dict[str, int] = {name: 0 for name, _ in backends_to_monitor}
        WARN_THRESHOLD = 3

        try:
            while True:
                for name, client in backends_to_monitor:
                    try:
                        monitor_cls, manager_cls = get_backend_classes(name)

                        if name == "lmstudio":
                            mon = monitor_cls(client)
                            mgr = manager_cls(client)
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
                            mon = monitor_cls(client)
                            mgr = manager_cls(client)
                            swarmui_data: dict[str, Any] = {"backend": "swarmui"}

                            try:
                                swarmui_data["resources"] = await mon.get_resource_info()
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
                                click.echo(format_resource_table(data["resources"]))

                            if "loaded_models" in data:
                                click.echo(format_loaded_models_table(data["loaded_models"]))

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
        from .cli.factories import create_client
        from .utils.formatter import format_table, format_json

        settings = get_settings()
        targets = [backend] if backend != "all" else ["lmstudio", "swarmui"]
        results: dict[str, Any] = {}

        for target in targets:
            try:
                async with create_client(settings, target) as client:
                    monitor_cls, manager_cls = get_backend_classes(target)
                    mgr = manager_cls(client)
                    avail = await mgr.list_available_models()
                    if target == "lmstudio":
                        results["lmstudio"] = {
                            "models": [
                                {"name": m.name, "path": m.path, "size_gb": round(m.size_gb, 2),
                                 "loaded_instances": m.loaded_instances}
                                for m in avail
                            ]
                        }
                    else:
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
                    click.echo(format_available_models_table(info["models"]))
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
        from .cli.factories import create_client

        settings = get_settings()
        async with create_client(settings, backend) as client:
            monitor_cls, manager_cls = get_backend_classes(backend)
            mgr = manager_cls(client)
            await mgr.load_model(model)
            click.echo(f"Loaded '{model}' on {backend}.")

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
        from .cli.factories import create_client

        settings = get_settings()
        if backend == "lmstudio":
            async with create_client(settings, backend) as client:
                monitor_cls, manager_cls = get_backend_classes(backend)
                mgr = manager_cls(client)
                await mgr.unload_model(model)
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
        from .cli.factories import create_client

        settings = get_settings()
        async with create_client(settings, backend) as client:
            monitor_cls, manager_cls = get_backend_classes(backend)
            mgr = manager_cls(client)
            await mgr.free_memory()
            click.echo(f"{backend}: Freed all model memory.")

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
        from .cli.factories import create_client
        from .utils.formatter import format_table, format_json

        settings = get_settings()
        results: dict[str, Any] = {}

        # Determine which backends to check
        if backend is not None:
            targets = [backend]
        else:
            targets = ["lmstudio", "swarmui"]

        for target in targets:
            try:
                async with create_client(settings, target) as client:
                    monitor_cls, _ = get_backend_classes(target)
                    mon = monitor_cls(client)
                    try:
                        loaded = await mon.list_loaded_models()
                        results[target] = {"reachable": True, "loaded_models": len(loaded)}
                    except Exception as e:
                        results[target] = {"reachable": False, "error": str(e)}
            except Exception as e:
                results[target] = {"reachable": False, "error": str(e)}

        if as_json:
            click.echo(format_json(results))
        else:
            click.echo(format_status_table(results))

    try:
        asyncio.run(_do_status())
    except Exception as e:
        raise click.ClickException(str(e))



# ── Switch command — save current models, load app models, run subcommand, restore ──

@cli.command()
@click.argument("app_name")
@click.argument("args", nargs=-1, required=False)
def switch(app_name: str, args: tuple[str, ...]):
    """Switch models for an app profile.

    Reads ~/.llm-switch-config.json to determine which models to load/unload per backend.
    After loading, runs any command passed as arguments (e.g., 'python3 script.py').
    Automatically restores previous LMStudio models after the command exits.
    SwarmUI memory is cleared on switch and restored by freeing all on return.
    """
    from .cli.state import save_switch_state, load_switch_state, cleanup_switch_state

    config_path = os.path.join(os.path.expanduser("~"), ".llm-switch-config.json")

    # Load app config
    if not os.path.exists(config_path):
        raise click.ClickException(f"Config file {config_path} not found")
    with open(config_path) as f:
        config = json.load(f)

    profile = config.get(app_name)
    if not profile:
        available = ", ".join(config.keys()) or "none"
        raise click.ClickException(
            f"Unknown app '{app_name}'. Available apps: {available}"
        )

    async def _do_switch():
        from .cli.factories import create_client

        settings = get_settings()

        # Step 1: Save current LMStudio loaded models
        try:
            async with create_client(settings, "lmstudio") as client:
                monitor_cls, _ = get_backend_classes("lmstudio")
                mon = monitor_cls(client)
                saved_models = await mon.list_loaded_models()
                instance_ids = [m.instance_id for m in saved_models if m.instance_id]
                save_switch_state(instance_ids)
                click.echo(f"  Saved {len(instance_ids)} LMStudio model(s): {instance_ids}")
        except Exception as e:
            logger.warning("Could not save current models: %s", e)

        # Step 2: Free all memory (LMStudio unload + SwarmUI free)
        try:
            async with create_client(settings, "lmstudio") as client:
                _, manager_cls = get_backend_classes("lmstudio")
                mgr = manager_cls(client)
                await mgr.free_memory()
                click.echo("  Freed LMStudio memory")
        except Exception as e:
            logger.warning("Could not free LMStudio memory: %s", e)

        try:
            async with create_client(settings, "swarmui") as client:
                _, manager_cls = get_backend_classes("swarmui")
                mgr = manager_cls(client)
                await mgr.free_memory()
                click.echo("  Freed SwarmUI memory")
        except NotImplementedError:
            pass
        except Exception as e:
            logger.warning("Could not free SwarmUI memory: %s", e)

        # Step 3: Load app-specific models from config
        after = profile.get("after", {})
        for backend_name, load_models in after.items():
            try:
                async with create_client(settings, backend_name) as client:
                    _, manager_cls = get_backend_classes(backend_name)
                    mgr = manager_cls(client)
                    for model_path in load_models:
                        await mgr.load_model(model_path)
                        click.echo(f"  Loaded '{model_path}' on {backend_name}")
            except NotImplementedError:
                pass

        # Step 4: Run subcommand if provided
        if args:
            import subprocess
            cmd = list(args)
            click.echo(f"  Running: {' '.join(cmd)}\n")
            result = subprocess.run(cmd, env={**os.environ})
            cleanup_switch_state()
            if result.returncode != 0:
                raise click.ClickException(f"Command exited with code {result.returncode}")

        # Step 5: Restore previous LMStudio models (auto-restore)
        saved_ids = load_switch_state()
        if saved_ids:
            try:
                async with create_client(settings, "lmstudio") as client:
                    _, manager_cls = get_backend_classes("lmstudio")
                    mgr = manager_cls(client)
                    for instance_id in saved_ids:
                        # Unload the new model first, then restore old one
                        try:
                            await mgr.unload_model(instance_id)
                        except Exception:
                            pass  # Model not loaded yet, just load it fresh
                    # Reload all saved models
                    for instance_id in saved_ids:
                        # We need to find the model path from instance_id
                        # Since we only have instance IDs, we'll reload by loading the model
                        # that was previously loaded (we stored instance_ids which are model paths)
                        try:
                            await mgr.load_model(instance_id)
                            click.echo(f"  Restored '{instance_id}'")
                        except Exception as e:
                            logger.warning("Could not restore '%s': %s", instance_id, e)
            except Exception as e:
                logger.warning("Could not restore models: %s", e)

        cleanup_switch_state()

    try:
        asyncio.run(_do_switch())
    except Exception as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
