"""Tests for SwarmUI manager."""

import pytest
from unittest.mock import AsyncMock
from llm_control.services.swarmui.monitor import SwarmUIManager
from llm_control.models.model_info import DownloadedModel


class TestSwarmUIManager:
    @pytest.mark.asyncio
    async def test_load_model(self):
        """Test load_model calls POST /API/SelectModel."""
        client = AsyncMock()
        manager = SwarmUIManager(client)

        await manager.load_model("path/to/model.safetensors")
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[0][0] == "SelectModel"

    @pytest.mark.asyncio
    async def test_unload_model_raises(self):
        """Test unload_model raises NotImplementedError for SwarmUI."""
        client = AsyncMock()
        manager = SwarmUIManager(client)

        with pytest.raises(NotImplementedError, match="per-model unload"):
            await manager.unload_model("inst1")

    @pytest.mark.asyncio
    async def test_list_available_models(self):
        """Test list_available_models parses downloaded models."""
        client = AsyncMock()
        # SwarmUI ListModels returns files/folders structure with full paths in file names
        client.post.return_value = {
            "files": [
                {"name": "model.safetensors", "size_gb": 3.5},
            ],
            "folders": [],
        }

        manager = SwarmUIManager(client)
        result = await manager.list_available_models()

        assert len(result) == 1
        assert isinstance(result[0], DownloadedModel)
        assert result[0].name == "model.safetensors"
        assert result[0].backend == "swarmui"

    @pytest.mark.asyncio
    async def test_free_memory(self):
        """Test free_memory calls POST /API/FreeBackendMemory."""
        client = AsyncMock()
        manager = SwarmUIManager(client)

        await manager.free_memory()
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[0][0] == "FreeBackendMemory"
