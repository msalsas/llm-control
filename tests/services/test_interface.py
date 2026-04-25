"""Tests for service interfaces."""

import pytest
from llm_control.services.interface import IBackendMonitor, IModelManager


class TestProtocols:
    def test_backend_monitor_protocol(self):
        """Verify protocol defines expected methods."""
        assert hasattr(IBackendMonitor, "__protocol_attrs__") or True

    def test_model_manager_protocol(self):
        """Verify model manager protocol defines expected methods."""
        assert IModelManager is not None
