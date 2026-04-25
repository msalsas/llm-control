"""Tests for LMStudio manager."""

import pytest
from unittest.mock import AsyncMock
from llm_control.services.lmstudio.monitor import LmStudioManager
from llm_control.models.model_info import DownloadedModel


class TestLmStudioManager:
    @pytest.mark.asyncio
    async def test_load_model(self):
        """Test load_model calls POST /api/v1/models/load."""
        client = AsyncMock()
        manager = LmStudioManager(client)

        await manager.load_model("microsoft/Phi-3-mini")
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[0][0] == "models/load"

    @pytest.mark.asyncio
    async def test_unload_model(self):
        """Test unload_model calls POST /api/v1/models/unload."""
        client = AsyncMock()
        manager = LmStudioManager(client)

        await manager.unload_model("inst1")
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[0][0] == "models/unload"
        payload = call_args[1]["payload"] if "payload" in call_args else call_args[0][1]
        assert payload["instance_id"] == "inst1"

    @pytest.mark.asyncio
    async def test_list_available_models(self):
        """Test list_available_models parses downloaded models."""
        client = AsyncMock()
        client.get.return_value = [
            {
                "name": "microsoft/Phi-3-mini",
                "path": "/models/phi-3-mini.gguf",
                "loaded_instances": [{"instance_id": "inst1"}],
            }
        ]

        manager = LmStudioManager(client)
        result = await manager.list_available_models()

        assert len(result) == 1
        assert isinstance(result[0], DownloadedModel)
        assert result[0].name == "microsoft/Phi-3-mini"
        assert result[0].backend == "lmstudio"

    @pytest.mark.asyncio
    async def test_free_memory_unloads_all(self):
        """Test free_memory lists loaded → unloads each one."""
        client = AsyncMock()
        client.get.return_value = [
            {
                "name": "microsoft/Phi-3-mini",
                "loaded_instances": [{"instance_id": "inst1"}, {"instance_id": "inst2"}],
            }
        ]

        manager = LmStudioManager(client)
        await manager.free_memory()

        # Should have unloaded each instance
        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_free_memory_handles_errors(self):
        """Test free_memory continues on unload errors."""
        client = AsyncMock()
        client.get.return_value = [
            {"name": "test", "loaded_instances": [{"instance_id": "inst1"}]}
        ]

        async def fail_unload(*args, **kwargs):
            raise RuntimeError("unload failed")

        client.post.side_effect = fail_unload

        manager = LmStudioManager(client)
        await manager.free_memory()  # Should not raise
