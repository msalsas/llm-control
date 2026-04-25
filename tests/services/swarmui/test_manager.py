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
    async def test_list_available_models_recursive(self):
        """Test list_available_models walks into sub-folders recursively."""
        client = AsyncMock()

        # First call: root — one file, one folder
        root_response = {
            "files": [{"name": "root_model.safetensors", "size_gb": 1.0}],
            "folders": ["SubFolder"],
        }
        # Second call: SubFolder — one file, no more folders
        sub_response = {
            "files": [{"name": "SubFolder/sub_model.safetensors", "size_gb": 2.0}],
            "folders": [],
        }
        client.post.side_effect = [root_response, sub_response]

        manager = SwarmUIManager(client)
        result = await manager.list_available_models()

        assert len(result) == 2
        assert result[0].name == "root_model.safetensors"
        assert result[1].name == "SubFolder/sub_model.safetensors"

    @pytest.mark.asyncio
    async def test_walk_model_dir_non_dict_response(self):
        """Test _walk_model_dir returns early when response is not a dict."""
        client = AsyncMock()
        client.post.return_value = ["not", "a", "dict"]

        manager = SwarmUIManager(client)
        models = []
        await manager._walk_model_dir("", models)
        assert models == []

    @pytest.mark.asyncio
    async def test_walk_model_dir_non_dict_file_items(self):
        """Test _walk_model_dir skips file items that are not dicts."""
        client = AsyncMock()
        client.post.return_value = {
            "files": ["just-a-string", 42],
            "folders": [],
        }

        manager = SwarmUIManager(client)
        models = []
        await manager._walk_model_dir("", models)
        assert models == []

    @pytest.mark.asyncio
    async def test_walk_model_dir_non_string_folder_items(self):
        """Test _walk_model_dir skips folder items that are not strings."""
        client = AsyncMock()

        root_response = {
            "files": [],
            "folders": [{"not": "a string"}, None, 123],
        }
        client.post.return_value = root_response

        manager = SwarmUIManager(client)
        models = []
        await manager._walk_model_dir("", models)
        assert models == []

    @pytest.mark.asyncio
    async def test_free_memory(self):
        """Test free_memory calls POST /API/FreeBackendMemory."""
        client = AsyncMock()
        manager = SwarmUIManager(client)

        await manager.free_memory()
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[0][0] == "FreeBackendMemory"

    @pytest.mark.asyncio
    async def test_free_memory_handles_exception(self):
        """Test free_memory logs a warning when the call fails instead of raising."""
        client = AsyncMock()
        client.post.side_effect = Exception("connection refused")

        manager = SwarmUIManager(client)
        # Should not raise — errors are caught and logged
        await manager.free_memory()
