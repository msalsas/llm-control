"""Model information data models."""

from pydantic import BaseModel


class LoadedModel(BaseModel):
    """Information about a currently loaded model."""

    name: str
    instance_id: str | None = None
    backend: str = ""
    vram_allocated: float = 0.0


class DownloadedModel(BaseModel):
    """Information about a downloaded (but not necessarily loaded) model."""

    name: str
    path: str = ""
    size_gb: float = 0.0
    backend: str = ""
    loaded_instances: list[str] = []
