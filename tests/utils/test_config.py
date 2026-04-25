"""Tests for configuration."""

import pytest
from llm_control.utils.config import Settings


class TestSettings:
    def test_defaults(self):
        settings = Settings()
        assert settings.lmstudio_base_url == "http://localhost:1234"
        assert settings.swarmui_base_url == "http://localhost:7801"
        assert settings.poll_interval == 30

    def test_retry_intervals_default(self):
        """Retry intervals default to (1, 2, 5) for CLI interactivity."""
        settings = Settings()
        assert settings.retry_intervals == (1, 2, 5)
