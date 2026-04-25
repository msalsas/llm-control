"""Tests for formatter."""

import pytest
from src.llm_control.utils.formatter import format_table, format_json, parse_model_list


class TestFormatTable:
    def test_basic_table(self):
        headers = ["Name", "VRAM"]
        rows = [["Phi-3-mini", "4.5GB"], ["Llama-2", "8.0GB"]]
        result = format_table(rows, headers)
        assert "Name" in result
        assert "VRAM" in result
        assert "Phi-3-mini" in result

    def test_empty_headers(self):
        result = format_table([], [])
        assert result == ""

    def test_single_row(self):
        headers = ["Key", "Value"]
        rows = [["test", "123"]]
        result = format_table(rows, headers)
        lines = result.split("\n")
        assert len(lines) == 3  # header + separator + row


class TestFormatJson:
    def test_format_dict(self):
        data = {"name": "test", "value": 42}
        result = format_json(data)
        assert '"name"' in result
        assert '"value"' in result

    def test_format_list(self):
        data = [1, 2, 3]
        result = format_json(data)
        assert "[1, 2, 3]" in result or "1" in result


class TestParseModelList:
    def test_list_passthrough(self):
        data = [{"name": "a"}, {"name": "b"}]
        assert parse_model_list(data) == data

    def test_dict_with_models_key(self):
        data = {"models": [{"name": "x"}]}
        assert parse_model_list(data) == [{"name": "x"}]

    def test_dict_with_loaded_models_key(self):
        data = {"loaded_models": [{"name": "y"}]}
        assert parse_model_list(data) == [{"name": "y"}]

    def test_dict_with_available_models_key(self):
        data = {"available_models": [{"name": "z"}]}
        assert parse_model_list(data) == [{"name": "z"}]

    def test_dict_with_downloaded_key(self):
        data = {"downloaded": [{"name": "w"}]}
        assert parse_model_list(data) == [{"name": "w"}]

    def test_unknown_input_returns_empty(self):
        """parse_model_list should return [] for unrecognized input types."""
        assert parse_model_list("unexpected string") == []
        assert parse_model_list(42) == []
        assert parse_model_list({"unknown_key": [1, 2]}) == []
