"""SwarmUI monitor and manager — business logic layer."""

import logging
from typing import Any

from llm_control.models.resource import ResourceUsage, GPUStats
from llm_control.models.model_info import LoadedModel, DownloadedModel
from llm_control.models.backend_status import ServerStatus, BackendStatus
from llm_control.services.swarmui.client import SwarmUIClient
from llm_control.utils.formatter import parse_model_list

logger = logging.getLogger(__name__)


class SwarmUIMonitor:
    """Collects and transforms monitoring data from SwarmUI."""

    def __init__(self, client: SwarmUIClient):
        self.client = client

    async def get_resource_info(self) -> ResourceUsage:
        """Get resource info from /API/GetServerResourceInfo.

        Returns VRAM, RAM, CPU stats from the SwarmUI backend.
        """
        data = await self.client.post("GetServerResourceInfo")
        # Parse the response — SwarmUI returns GPU stats with VRAM/RAM/CPU
        vram_used = 0.0
        vram_total = 0.0
        ram_used = 0.0
        ram_total = 0.0
        cpu_usage = 0.0
        gpu_count = 0

        # Handle various response formats
        if isinstance(data, dict):
            # Check for GPU array
            gpus = data.get("gpus", [])
            if isinstance(gpus, list):
                gpu_count = len(gpus)
                for gpu in gpus:
                    if isinstance(gpu, dict):
                        vram_used += gpu.get("vram_used", 0.0)
                        vram_total += gpu.get("vram_total", 0.0)

            # Check for RAM/CPU info
            ram_info = data.get("ram", {})
            if isinstance(ram_info, dict):
                ram_used = ram_info.get("used", 0.0)
                ram_total = ram_info.get("total", 0.0)

            cpu_info = data.get("cpu", {})
            if isinstance(cpu_info, dict):
                cpu_usage = cpu_info.get("usage_percent", 0.0)

        return ResourceUsage(
            vram_used=vram_used,
            vram_total=vram_total,
            ram_used=ram_used,
            ram_total=ram_total,
            cpu_usage=cpu_usage,
            gpu_count=gpu_count,
        )

    async def get_server_status(self) -> ServerStatus:
        """Get server status from /API/GetGlobalStatus."""
        data = await self.client.post("GetGlobalStatus")
        backends: dict[str, BackendStatus] = {}

        if isinstance(data, dict):
            # Extract backend info
            for key, value in data.items():
                reachable = False
                loaded_models: list[str] = []

                if isinstance(value, dict):
                    reachable = value.get("online", value.get("active", False))
                    models = value.get("models", [])
                    if isinstance(models, list):
                        loaded_models = [m.get("name", str(m)) for m in models]

                backends[key] = BackendStatus(
                    name=key, base_url="", reachable=reachable, loaded_models=loaded_models
                )

        return ServerStatus(backends=backends)

    async def list_loaded_models(self) -> list[LoadedModel]:
        """List loaded models from /API/ListLoadedModels."""
        data = await self.client.post("ListLoadedModels")
        models: list[LoadedModel] = []

        # Use shared parser to handle dict-with-list responses
        items = parse_model_list(data)
        for item in items:
            if isinstance(item, dict):
                name = item.get("name", item.get("model", "unknown"))
                instance_id = item.get("instance_id", "")
                vram = item.get("vram_allocated", 0.0)
                models.append(
                    LoadedModel(name=name, instance_id=instance_id, backend="swarmui", vram_allocated=vram)
                )
            elif isinstance(item, str):
                models.append(LoadedModel(name=item, backend="swarmui"))

        return models


class SwarmUIManager:
    """Manages model lifecycle for SwarmUI."""

    def __init__(self, client: SwarmUIClient):
        self.client = client

    async def load_model(self, model_path: str) -> None:
        """Load a model via /API/SelectModel."""
        await self.client.post("SelectModel", {"model": model_path})
        logger.info("Loaded model '%s' on SwarmUI", model_path)

    async def unload_model(self, instance_id: str) -> None:
        """SwarmUI does NOT support per-model unload.

        Use free_memory() instead to clear ALL loaded models from all backends.
        """
        raise NotImplementedError(
            "SwarmUI doesn't support per-model unload. "
            "Use `free-memory` instead."
        )

    async def list_available_models(self) -> list[DownloadedModel]:
        """List downloaded models via /API/ListModels.

        SwarmUI requires path and depth parameters to enumerate the model directory.
        Recursively walks all subfolders to return a complete model listing.
        """
        models: list[DownloadedModel] = []
        await self._walk_model_dir("", models)
        return models

    async def _walk_model_dir(self, path: str, models: list[DownloadedModel]) -> None:
        """Recursively walk the model directory collecting all files."""
        data = await self.client.post("ListModels", {"path": path, "depth": 0})

        if not isinstance(data, dict):
            return

        # SwarmUI returns full paths in file names (e.g. "ZImage/file.safetensors")
        for item in data.get("files", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name", item.get("title", "unknown"))
            # Use the API's full path directly — it already includes folder prefix
            file_path = item.get("name", "")
            size = item.get("size_gb", 0.0)
            models.append(
                DownloadedModel(name=name, path=file_path, size_gb=size, backend="swarmui")
            )

        # Recurse into subfolders (API returns folder names without full paths)
        for folder in data.get("folders", []):
            if not isinstance(folder, str):
                continue
            child = f"{path}/{folder}" if path else folder
            await self._walk_model_dir(child, models)

    async def free_memory(self) -> None:
        """Clear ALL loaded models from ALL backends via /API/FreeBackendMemory.

        This is the only option available in SwarmUI — no per-model unload exists.
        Errors are logged without raising for consistent behavior across backends.
        """
        try:
            await self.client.post("FreeBackendMemory")
            logger.info("SwarmUI: Cleared all backend memory")
        except Exception as e:
            logger.warning("Failed to free SwarmUI memory: %s", e)
