"""Tests for CLI presentation views."""

import pytest

from llm_control.cli.views import (
    format_resource_table,
    format_loaded_models_table,
    format_available_models_table,
    format_status_table,
)
from llm_control.models.resource import ResourceUsage


class TestFormatResourceTable:
    """Test resource table formatting."""

    def test_basic_format(self):
        resources = ResourceUsage(
            vram_used=8.0, vram_total=16.0,
            ram_used=4.0, ram_total=32.0,
            cpu_usage=45.5, gpu_count=2,
        )
        result = format_resource_table(resources)
        assert "VRAM Used" in result
        assert "8.00 GB" in result
        assert "GPU Count" in result
        assert "2" in result

    def test_header_and_separator(self):
        resources = ResourceUsage()
        lines = format_resource_table(resources).split("\n")
        # First line is header, second is separator
        assert "|" in lines[0]
        assert "-" in lines[1]


class TestFormatLoadedModelsTable:
    """Test loaded models table formatting."""

    def test_with_vram(self):
        models = [
            {"name": "model1", "instance_id": "inst1", "vram_allocated_gb": 4.5},
            {"name": "model2", "instance_id": "inst2", "vram_allocated_gb": 2.0},
        ]
        result = format_loaded_models_table(models)
        assert "VRAM (GB)" in result
        assert "Name" in result

    def test_without_vram(self):
        models = [
            {"name": "model1", "instance_id": "inst1"},
        ]
        result = format_loaded_models_table(models)
        assert "VRAM" not in result
        assert "No models loaded." not in result

    def test_empty_returns_no_models_message(self):
        result = format_loaded_models_table([])
        assert "No models loaded." in result


class TestFormatAvailableModelsTable:
    """Test available models table formatting."""

    def test_with_size_and_loaded(self):
        models = [
            {"name": "model1", "path": "/models/model1.gguf", "size_gb": 3.5, "loaded_instances": ["inst1"]},
        ]
        result = format_available_models_table(models)
        assert "Size (GB)" in result
        assert "Loaded Instances" in result

    def test_with_size_only(self):
        models = [
            {"name": "model1", "path": "/models/model1.gguf", "size_gb": 3.5},
        ]
        result = format_available_models_table(models)
        assert "Size (GB)" in result
        assert "Loaded Instances" not in result

    def test_without_size(self):
        models = [
            {"name": "model1", "path": "/models/model1.gguf"},
        ]
        result = format_available_models_table(models)
        headers = result.split("\n")[0]
        assert "Name" in headers
        assert "Size" not in headers

    def test_empty_returns_no_models_message(self):
        result = format_available_models_table([])
        assert "No models available." in result


class TestFormatStatusTable:
    """Test status table formatting."""

    def test_all_reachable(self):
        results = {
            "lmstudio": {"reachable": True, "loaded_models": 2},
            "swarmui": {"reachable": True, "loaded_models": 1},
        }
        result = format_status_table(results)
        assert "Backend" in result
        assert "Yes" in result

    def test_unreachable_with_error(self):
        results = {
            "lmstudio": {"reachable": False, "error": "Connection refused"},
        }
        result = format_status_table(results)
        assert "No" in result
        assert "Connection refused" in result
