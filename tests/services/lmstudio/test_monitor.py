"""Tests for LMStudio monitor."""

import pytest
from unittest.mock import AsyncMock
from llm_control.services.lmstudio.monitor import LmStudioMonitor
from llm_control.models.resource import ResourceUsage
from llm_control.models.model_info import LoadedModel


class TestLmStudioMonitor:
    @pytest.mark.asyncio
    async def test_get_resource_info_raises(self):
        """LMStudio has no resource telemetry — should raise NotImplementedError."""
        client = AsyncMock()
        monitor = LmStudioMonitor(client)

        with pytest.raises(NotImplementedError, match="VRAM"):
            await monitor.get_resource_info()

    @pytest.mark.asyncio
    async def test_get_server_status_raises(self):
        """LMStudio has no server status endpoint — should raise NotImplementedError."""
        client = AsyncMock()
        monitor = LmStudioMonitor(client)

        with pytest.raises(NotImplementedError, match="server status"):
            await monitor.get_server_status()

    @pytest.mark.asyncio
    async def test_list_loaded_models(self):
        """Test parsing loaded models from /api/v1/models response."""
        client = AsyncMock()
        client.get.return_value = [
            {
                "name": "microsoft/Phi-3-mini",
                "loaded_instances": [{"instance_id": "inst1"}],
            },
            {
                "name": "Llama-2-7b",
                "loaded_instances": [{"instance_id": "inst2"}, {"instance_id": "inst3"}],
            },
        ]

        monitor = LmStudioMonitor(client)
        result = await monitor.list_loaded_models()

        assert len(result) == 3
        assert isinstance(result[0], LoadedModel)
        assert result[0].name == "microsoft/Phi-3-mini"
        assert result[0].instance_id == "inst1"
        assert result[2].instance_id == "inst3"

    @pytest.mark.asyncio
    async def test_list_loaded_models_empty(self):
        """Test with no loaded models."""
        client = AsyncMock()
        client.get.return_value = []

        monitor = LmStudioMonitor(client)
        result = await monitor.list_loaded_models()
        assert result == []
