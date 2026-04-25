"""Tests for connection configuration."""

import pytest
from llm_control.models.connection import ConnectionConfig


class TestConnectionConfig:
    def test_create_basic(self):
        config = ConnectionConfig(base_url="http://localhost:1234")
        assert config.base_url == "http://localhost:1234"
        assert config.token is None

    def test_create_with_token(self):
        config = ConnectionConfig(
            base_url="http://localhost:1234", token="secret-token"
        )
        assert config.base_url == "http://localhost:1234"
        assert config.token == "secret-token"

    def test_to_dict(self):
        config = ConnectionConfig(base_url="http://localhost:1234")
        d = config.model_dump()
        assert d["base_url"] == "http://localhost:1234"
        assert d["token"] is None
