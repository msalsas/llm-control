"""Configuration loading from environment."""

import os
from typing import Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables.

    Loads .env file if present in CWD; falls back to environment variables.
    No error is raised if .env is missing — this allows flexible development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    lmstudio_base_url: str = "http://localhost:1234"
    swarmui_base_url: str = "http://localhost:7801"
    lmstudio_token: str | None = None
    swarmui_token: str | None = None
    poll_interval: int = 30

    # Retry configuration — default (1, 2, 5) seconds for CLI interactivity
    retry_intervals: Tuple[int, ...] = (1, 2, 5)
