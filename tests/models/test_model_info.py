"""Tests for model info data models."""

import pytest
from llm_control.models.model_info import LoadedModel, DownloadedModel


class TestLoadedModel:
    def test_create_loaded_model(self):
        model = LoadedModel(name="microsoft/Phi-3-mini", instance_id="inst1", backend="lmstudio")
        assert model.name == "microsoft/Phi-3-mini"
        assert model.instance_id == "inst1"

    def test_defaults(self):
        model = LoadedModel(name="test-model")
        assert model.instance_id is None
        assert model.backend == ""
        assert model.vram_allocated == 0.0


class TestDownloadedModel:
    def test_create_downloaded_model(self):
        model = DownloadedModel(
            name="model.safetensors", path="/models/model.safetensors", size_gb=3.5, backend="swarmui"
        )
        assert model.name == "model.safetensors"
        assert model.size_gb == 3.5

    def test_defaults(self):
        model = DownloadedModel(name="test-model")
        assert model.path == ""
        assert model.loaded_instances == []
