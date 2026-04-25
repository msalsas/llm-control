"""Tests for SwarmUI monitor."""

import pytest
from unittest.mock import AsyncMock
from llm_control.services.swarmui.monitor import SwarmUIMonitor
from llm_control.models.resource import ResourceUsage
from llm_control.models.model_info import LoadedModel


class TestSwarmUIMonitor:
    @pytest.mark.asyncio
    async def test_get_resource_info(self):
        """Test parsing resource info from GetServerResourceInfo."""
        client = AsyncMock()
        # SwarmUI returns VRAM/RAM in bytes, CPU usage as percentage
        GB = 1024 ** 3
        client.post.return_value = {
            "gpus": {
                "0": {"used_memory": 4.5 * GB, "total_memory": 8.0 * GB},
                "1": {"used_memory": 2.0 * GB, "total_memory": 8.0 * GB},
            },
            "system_ram": {"used": 16.0 * GB, "total": 32.0 * GB},
            "cpu": {"usage": 45.0},
        }

        monitor = SwarmUIMonitor(client)
        result = await monitor.get_resource_info()

        assert isinstance(result, ResourceUsage)
        assert result.vram_used == pytest.approx(6.5)
        assert result.vram_total == pytest.approx(16.0)
        assert result.gpu_count == 2
        assert result.ram_used == pytest.approx(16.0)
        assert result.ram_total == pytest.approx(32.0)
        assert result.cpu_usage == 45.0

    @pytest.mark.asyncio
    async def test_get_resource_info_empty(self):
        """Test with empty response."""
        client = AsyncMock()
        client.post.return_value = {}

        monitor = SwarmUIMonitor(client)
        result = await monitor.get_resource_info()

        assert result.vram_used == 0.0
        assert result.gpu_count == 0

    @pytest.mark.asyncio
    async def test_list_loaded_models(self):
        """Test parsing loaded models from ListLoadedModels."""
        client = AsyncMock()
        client.post.return_value = {
            "models": [
                {"name": "microsoft/Phi-3-mini", "instance_id": "inst1", "vram_allocated": 4.0},
                {"name": "Llama-2-7b", "instance_id": "inst2"},
            ]
        }

        monitor = SwarmUIMonitor(client)
        result = await monitor.list_loaded_models()

        assert len(result) == 2
        assert isinstance(result[0], LoadedModel)
        assert result[0].name == "microsoft/Phi-3-mini"
        assert result[0].vram_allocated == 4.0

    @pytest.mark.asyncio
    async def test_get_server_status(self):
        """Test parsing server status from GetGlobalStatus."""
        client = AsyncMock()
        client.post.return_value = {
            "lmstudio": {"online": True, "models": [{"name": "phi-3"}]},
            "swarmui": {"online": False},
        }

        monitor = SwarmUIMonitor(client)
        result = await monitor.get_server_status()

        assert "lmstudio" in result.backends
        assert result.backends["lmstudio"].reachable is True
