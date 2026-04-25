"""Configuration loading from environment."""

import os
from typing import Tuple

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to the project root (where .env lives)
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../src/llm_control/utils
_PROJECT_ROOT = os.path.realpath(os.path.join(_PACKAGE_DIR, "..", "..", ".."))  # .../llm-control
_SETTINGS_ENV = os.path.join(_PROJECT_ROOT, ".env")


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables.

    Loads .env file relative to the package directory; falls back to
    environment variables (e.g. exported in ~/.bashrc).
    No error is raised if .env is missing — this allows flexible development.
    """

    model_config = SettingsConfigDict(
        env_file=_SETTINGS_ENV,
        extra="ignore",
    )

    lmstudio_base_url: str = "http://localhost:1234"
    swarmui_base_url: str = "http://localhost:7801"
    lmstudio_token: str | None = None
    swarmui_token: str | None = None
    poll_interval: int = 30

    # Retry configuration — default (1, 2, 5) seconds for CLI interactivity
    retry_intervals: Tuple[int, ...] = (1, 2, 5)
