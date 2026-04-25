"""Tests for backend status data models."""

import pytest
from llm_control.models.backend_status import BackendStatus, ServerStatus


class TestBackendStatus:
    def test_create_backend_status(self):
        status = BackendStatus(name="lmstudio", base_url="http://localhost:1234", reachable=True)
        assert status.name == "lmstudio"
        assert status.reachable is True

    def test_with_error(self):
        status = BackendStatus(
            name="swarmui", base_url="http://localhost:7801",
            error="Connection refused"
        )
        assert status.error == "Connection refused"


class TestServerStatus:
    def test_create_server_status(self):
        status = ServerStatus()
        assert status.overall_healthy is True
        assert len(status.backends) == 0

    def test_with_backends(self):
        backend = BackendStatus(name="lmstudio", base_url="http://localhost:1234", reachable=True)
        status = ServerStatus(backends={"lmstudio": backend})
        assert "lmstudio" in status.backends
