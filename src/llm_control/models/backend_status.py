"""Backend status data models."""

from pydantic import BaseModel


class BackendStatus(BaseModel):
    """Status of a single backend."""

    name: str
    base_url: str
    reachable: bool = False
    loaded_models: list[str] = []
    error: str | None = None


class ServerStatus(BaseModel):
    """Aggregated status across all backends."""

    backends: dict[str, BackendStatus] = {}
    overall_healthy: bool = True
    errors: list[str] = []
