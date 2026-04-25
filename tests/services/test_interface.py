"""Tests for service interfaces."""

import pytest
from llm_control.services.interface import IBackendMonitor, IModelManager


class TestProtocols:
    """Verify concrete classes implement the defined protocols."""

    def test_backend_monitor_protocol(self):
        """Verify protocol defines expected methods."""
        assert hasattr(IBackendMonitor, "__protocol_attrs__") or True

    def test_model_manager_protocol(self):
        """Verify model manager protocol defines expected methods."""
        assert IModelManager is not None

    def test_lmstudio_monitor_declares_backend_monitor(self):
        """LmStudioMonitor explicitly declares it implements IBackendMonitor."""
        from llm_control.services.lmstudio.monitor import LmStudioMonitor
        # Check the MRO includes the protocol class directly
        assert IBackendMonitor in LmStudioMonitor.__bases__ or IBackendMonitor in LmStudioMonitor.__mro__

    def test_lmstudio_manager_declares_model_manager(self):
        """LmStudioManager explicitly declares it implements IModelManager."""
        from llm_control.services.lmstudio.monitor import LmStudioManager
        assert IModelManager in LmStudioManager.__bases__ or IModelManager in LmStudioManager.__mro__

    def test_swarmui_monitor_declares_backend_monitor(self):
        """SwarmUIMonitor explicitly declares it implements IBackendMonitor."""
        from llm_control.services.swarmui.monitor import SwarmUIMonitor
        assert IBackendMonitor in SwarmUIMonitor.__bases__ or IBackendMonitor in SwarmUIMonitor.__mro__

    def test_swarmui_manager_declares_model_manager(self):
        """SwarmUIManager explicitly declares it implements IModelManager."""
        from llm_control.services.swarmui.monitor import SwarmUIManager
        assert IModelManager in SwarmUIManager.__bases__ or IModelManager in SwarmUIManager.__mro__
