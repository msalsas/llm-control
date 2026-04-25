"""LMStudio monitor and manager — business logic layer."""

import logging
from typing import Any

from llm_control.models.resource import ResourceUsage
from llm_control.models.model_info import LoadedModel, DownloadedModel
from llm_control.models.backend_status import ServerStatus, BackendStatus
from llm_control.services.lmstudio.client import LmStudioClient
from llm_control.utils.formatter import parse_model_list

logger = logging.getLogger(__name__)


class LmStudioMonitor:
    """Collects and transforms monitoring data from LMStudio.

    Note: LMStudio v1 REST API does NOT expose per-model VRAM/RAM/CPU stats.
    Only loaded model info is available via the /api/v1/models endpoint.
    """

    def __init__(self, client: LmStudioClient):
        self.client = client

    async def get_resource_info(self) -> ResourceUsage:
        """LMStudio has no resource telemetry endpoints."""
        raise NotImplementedError(
            "LMStudio v1 REST API does not expose VRAM/RAM/CPU stats. "
            "Use SwarmUI for resource monitoring."
        )

    async def get_server_status(self) -> ServerStatus:
        """LMStudio has no server status endpoint."""
        raise NotImplementedError(
            "LMStudio v1 REST API does not have a server status endpoint."
        )

    async def list_loaded_models(self) -> list[LoadedModel]:
        """List loaded models from /api/v1/models response (loaded_instances)."""
        data = await self.client.get("models")
        models: list[LoadedModel] = []
        for model_entry in parse_model_list(data):
            for inst in model_entry.get("loaded_instances", []):
                instance_id = inst.get("instance_id", "") or inst.get("id", "")
                name = model_entry.get("display_name") or model_entry.get("key") or model_entry.get("name", "unknown")
                models.append(
                    LoadedModel(name=name, instance_id=instance_id, backend="lmstudio")
                )
        return models


class LmStudioManager:
    """Manages model lifecycle for LMStudio."""

    def __init__(self, client: LmStudioClient):
        self.client = client

    async def load_model(self, model_path: str) -> None:
        """Load a model via POST /api/v1/models/load."""
        payload: dict[str, Any] = {"model": model_path}
        await self.client.post("models/load", payload)

    async def unload_model(self, instance_id: str) -> None:
        """Unload a specific model instance via POST /api/v1/models/unload."""
        await self.client.post("models/unload", {"instance_id": instance_id})

    async def list_available_models(self) -> list[DownloadedModel]:
        """List all downloaded models from /api/v1/models."""
        data = await self.client.get("models")
        models: list[DownloadedModel] = []
        for model_entry in parse_model_list(data):
            name = model_entry.get("display_name") or model_entry.get("key") or model_entry.get("name", "unknown")
            model_key = model_entry.get("key", "")
            size_bytes = model_entry.get("size_bytes")
            size_gb = round(size_bytes / (1024 ** 3), 2) if size_bytes else 0.0
            loaded_ids = [
                inst.get("instance_id", "") or inst.get("id", "")
                for inst in model_entry.get("loaded_instances", [])
            ]
            models.append(
                DownloadedModel(name=name, path=model_key, size_gb=size_gb, backend="lmstudio", loaded_instances=loaded_ids)
            )
        return models

    async def free_memory(self) -> None:
        """Smart fallback: list loaded models → unload each one.

        LMStudio has no native 'free all' endpoint, but chaining per-model unloads
        achieves the same result. Individual unload errors are logged without raising.
        """
        data = await self.client.get("models")
        for model_entry in parse_model_list(data):
            for inst in model_entry.get("loaded_instances", []):
                instance_id = inst.get("instance_id", "") or inst.get("id", "")
                if instance_id:
                    try:
                        await self.unload_model(instance_id)
                    except Exception as e:
                        logger.warning("Failed to unload %s: %s", instance_id, e)
