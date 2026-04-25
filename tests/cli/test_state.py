"""Tests for CLI switch state management."""

import os
import tempfile
from unittest.mock import patch

import pytest


class TestSwitchState:
    """Test save/load/cleanup of switch state files."""

    def test_save_creates_file(self):
        from llm_control.cli.state import save_switch_state, load_switch_state, cleanup_switch_state

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch the state file path
            with patch("llm_control.cli.state._SWITCH_STATE_FILE", os.path.join(tmpdir, "state.json")):
                save_switch_state(["inst1", "inst2"])
                assert os.path.exists(os.path.join(tmpdir, "state.json"))

    def test_load_returns_saved_ids(self):
        from llm_control.cli.state import save_switch_state, load_switch_state, cleanup_switch_state

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            # Patch the file path
            original = __import__("llm_control.cli.state", fromlist=["_SWITCH_STATE_FILE"])
            original._SWITCH_STATE_FILE = state_file

            save_switch_state(["inst_a", "inst_b"])
            result = load_switch_state()
            assert result == ["inst_a", "inst_b"]

    def test_load_returns_empty_when_no_file(self):
        from llm_control.cli.state import load_switch_state, cleanup_switch_state

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "nonexistent.json")
            assert not os.path.exists(state_file)

            # Patch the file path to non-existent file
            original = __import__("llm_control.cli.state", fromlist=["_SWITCH_STATE_FILE"])
            original._SWITCH_STATE_FILE = state_file

            result = load_switch_state()
            assert result == []

    def test_cleanup_removes_file(self):
        from llm_control.cli.state import save_switch_state, cleanup_switch_state

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            original = __import__("llm_control.cli.state", fromlist=["_SWITCH_STATE_FILE"])
            original._SWITCH_STATE_FILE = state_file

            save_switch_state(["inst1"])
            assert os.path.exists(state_file)

            cleanup_switch_state()
            assert not os.path.exists(state_file)

    def test_cleanup_noop_when_no_file(self):
        """cleanup should not raise when file doesn't exist."""
        from llm_control.cli.state import cleanup_switch_state

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "nonexistent.json")
            original = __import__("llm_control.cli.state", fromlist=["_SWITCH_STATE_FILE"])
            original._SWITCH_STATE_FILE = state_file

            # Should not raise
            cleanup_switch_state()
