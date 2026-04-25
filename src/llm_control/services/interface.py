"""Service interfaces — protocols for backends."""

from typing import Protocol

from ..models.resource import ResourceUsage
from ..models.model_info import LoadedModel, DownloadedModel
from ..models.backend_status import ServerStatus


class IBackendMonitor(Protocol):
    """All monitors implement this. Some methods may raise NotImplementedError."""

    async def get_resource_info(self) -> ResourceUsage: ...  # SwarmUI only; LMStudio raises
    async def get_server_status(self) -> ServerStatus: ...   # SwarmUI only; LMStudio raises
    async def list_loaded_models(self) -> list[LoadedModel]: ...


class IModelManager(Protocol):
    """For load/unload/free-memory operations."""

    async def load_model(self, model_path: str) -> None: ...
    async def unload_model(self, instance_id: str) -> None: ...  # LMStudio only; SwarmUI raises
    async def list_available_models(self) -> list[DownloadedModel]: ...
    async def free_memory(self) -> None: ...                      # Both backends


class IClient(Protocol):
    """Low-level HTTP communication. Each backend handles its own session/auth internally."""

    async def get(self, path: str, **kwargs) -> dict: ...
    async def post(self, path: str, payload=None) -> dict: ...
