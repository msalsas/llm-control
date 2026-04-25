"""Connection configuration for backends."""

from pydantic import BaseModel


class ConnectionConfig(BaseModel):
    """Holds connection parameters for a backend."""

    base_url: str
    token: str | None = None
