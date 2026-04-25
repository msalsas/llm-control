"""Tests for formatter."""

import pytest
from src.llm_control.utils.formatter import format_table, format_json


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
