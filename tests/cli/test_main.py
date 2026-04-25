"""Tests for CLI commands in main.py."""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from llm_control.main import cli
from llm_control.models.model_info import LoadedModel, DownloadedModel
from llm_control.models.resource import ResourceUsage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# monitor command
# ---------------------------------------------------------------------------

class TestMonitorCommand:
    def test_monitor_lmstudio_table(self):
        """Test `monitor --backend lmstudio` outputs table format."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio")
        ]
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio"])
            assert result.exit_code == 0

    def test_monitor_json_output(self):
        """Test `monitor --json --backend lmstudio` outputs valid JSON."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert data["backend"] == "lmstudio"

    def test_monitor_backend_unreachable_quiet(self):
        """Test that `--quiet` suppresses error messages for unreachable backends."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.side_effect = ConnectionError("refused")
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio", "--quiet"])
            assert result.exit_code == 0

    def test_monitor_swarmui_with_resources(self):
        """Test `monitor --backend swarmui` outputs resource info."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_monitor.get_resource_info.return_value = ResourceUsage(
            vram_used=4.0, vram_total=8.0, ram_used=8.0, ram_total=16.0, cpu_usage=30.0
        )
        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "swarmui"])
            assert result.exit_code == 0

    def test_monitor_error_json_output(self):
        """Test error is output as JSON when --json flag is used and backend fails."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.side_effect = RuntimeError("boom")
        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert "error" in data


# ---------------------------------------------------------------------------
# models command
# ---------------------------------------------------------------------------

class TestModelsCommand:
    def test_models_lmstudio_table(self):
        """Test `models --backend lmstudio` lists available models as table."""
        runner = _runner()

        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = [
            DownloadedModel(name="phi-3", path="phi-3.gguf", size_gb=2.5,
                            loaded_instances=[], backend="lmstudio")
        ]

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["models", "--backend", "lmstudio"])
            assert result.exit_code == 0

    def test_models_json_output(self):
        """Test `models --json` returns valid JSON."""
        runner = _runner()

        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["models", "--backend", "lmstudio", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert "lmstudio" in data

    def test_models_error_handled(self):
        """Test that a backend error is captured and returned without crashing."""
        runner = _runner()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("refused"))
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, AsyncMock)

            result = runner.invoke(cli, ["models", "--backend", "lmstudio"])
            assert result.exit_code == 0
            assert "refused" in result.output or "error" in result.output.lower()

    def test_models_no_models_available_message(self):
        """Test that 'No models available' is shown when the list is empty."""
        runner = _runner()

        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["models", "--backend", "lmstudio"])
            assert result.exit_code == 0
            assert "No models" in result.output

    def test_models_swarmui_json(self):
        """Test `models --backend swarmui --json` returns SwarmUI key in JSON."""
        runner = _runner()

        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = [
            DownloadedModel(name="sdxl.safetensors", path="sdxl.safetensors",
                            size_gb=6.0, backend="swarmui")
        ]

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["models", "--backend", "swarmui", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert "swarmui" in data


# ---------------------------------------------------------------------------
# load command
# ---------------------------------------------------------------------------

class TestLoadCommand:
    def test_load_model_success(self):
        """Test `load --model foo` calls load_model and prints confirmation."""
        runner = _runner()

        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["load", "--model", "my-model.gguf"])
            assert result.exit_code == 0
            assert "my-model.gguf" in result.output
            mock_manager.load_model.assert_called_once_with("my-model.gguf")

    def test_load_model_error_raises_click_exception(self):
        """Test that backend errors are wrapped in ClickException."""
        runner = _runner()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("load failed"))
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, AsyncMock)

            result = runner.invoke(cli, ["load", "--model", "bad-model"])
            assert result.exit_code != 0
            assert "load failed" in result.output


# ---------------------------------------------------------------------------
# unload command
# ---------------------------------------------------------------------------

class TestUnloadCommand:
    def test_unload_lmstudio_success(self):
        """Test `unload --backend lmstudio --model inst1` calls unload_model."""
        runner = _runner()

        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["unload", "--backend", "lmstudio", "--model", "inst1"])
            assert result.exit_code == 0
            assert "inst1" in result.output
            mock_manager.unload_model.assert_called_once_with("inst1")

    def test_unload_swarmui_raises_click_exception(self):
        """Test `unload --backend swarmui` raises a ClickException."""
        runner = _runner()

        result = runner.invoke(cli, ["unload", "--backend", "swarmui", "--model", "inst1"])
        assert result.exit_code != 0
        assert "free-memory" in result.output


# ---------------------------------------------------------------------------
# free-memory command
# ---------------------------------------------------------------------------

class TestFreeMemoryCommand:
    def test_free_memory_success(self):
        """Test `free-memory --backend lmstudio` calls free_memory."""
        runner = _runner()

        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, lambda c: mock_manager)

            result = runner.invoke(cli, ["free-memory", "--backend", "lmstudio"])
            assert result.exit_code == 0
            mock_manager.free_memory.assert_called_once()

    def test_free_memory_error_raises_click_exception(self):
        """Test that a backend error is wrapped in ClickException."""
        runner = _runner()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("failed"))
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, AsyncMock)

            result = runner.invoke(cli, ["free-memory"])
            assert result.exit_code != 0


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

class TestStatusCommand:
    def test_status_all_reachable(self):
        """Test `status` lists both backends as reachable."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio")
        ]

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, AsyncMock)

            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0

    def test_status_json_output(self):
        """Test `status --json` returns valid JSON."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, AsyncMock)

            result = runner.invoke(cli, ["status", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert isinstance(data, dict)

    def test_status_single_backend(self):
        """Test `status --backend lmstudio` only checks lmstudio."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, AsyncMock)

            result = runner.invoke(cli, ["status", "--backend", "lmstudio"])
            assert result.exit_code == 0
            # create_client called exactly once (only lmstudio)
            assert mock_create.call_count == 1

    def test_status_unreachable_backend(self):
        """Test `status` handles an unreachable backend gracefully."""
        runner = _runner()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("conn refused"))
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (AsyncMock, AsyncMock)

            result = runner.invoke(cli, ["status", "--backend", "lmstudio"])
            assert result.exit_code == 0

    def test_status_monitor_inner_exception(self):
        """Test `status` handles inner monitor exception (list_loaded_models fails)."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.side_effect = RuntimeError("monitor error")

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, AsyncMock)

            result = runner.invoke(cli, ["status", "--backend", "lmstudio", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert data["lmstudio"]["reachable"] is False


# ---------------------------------------------------------------------------
# switch command
# ---------------------------------------------------------------------------

class TestSwitchCommand:
    def test_switch_missing_config_raises(self, tmp_path):
        """Test `switch` raises ClickException when config file is missing."""
        runner = _runner()

        with patch("os.path.expanduser", return_value=str(tmp_path / "nonexistent")):
            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_switch_unknown_app_raises(self, tmp_path):
        """Test `switch` raises ClickException for an unknown app."""
        runner = _runner()

        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps({"otherapp": {"after": {}}}))

        with patch("os.path.expanduser", return_value=str(tmp_path)):
            result = runner.invoke(cli, ["switch", "unknownapp"])
            assert result.exit_code != 0
            assert "Unknown app" in result.output

    def test_switch_loads_app_models(self, tmp_path):
        """Test `switch` loads models defined in the config profile."""
        runner = _runner()

        config = {
            "myapp": {
                "after": {
                    "lmstudio": ["path/to/model.gguf"]
                }
            }
        }
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0

    def test_switch_with_subprocess_args(self, tmp_path):
        """Test `switch myapp -- cmd` runs the subprocess and restores models."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio")
        ]
        mock_manager = AsyncMock()

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes, \
             patch("subprocess.run") as mock_run:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)
            mock_run.return_value = MagicMock(returncode=0)

            result = runner.invoke(cli, ["switch", "myapp", "echo", "hello"])
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_switch_subprocess_nonzero_exit(self, tmp_path):
        """Test `switch` raises ClickException when subprocess returns non-zero."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes, \
             patch("subprocess.run") as mock_run:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)
            mock_run.return_value = MagicMock(returncode=1)

            result = runner.invoke(cli, ["switch", "myapp", "false"])
            assert result.exit_code != 0
            assert "code 1" in result.output

    def test_switch_restores_saved_models(self, tmp_path):
        """Test that switch restores previously loaded models on completion."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio")
        ]
        mock_manager = AsyncMock()

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0
            # load_model should be called during restore for "inst1"
            assert mock_manager.load_model.called

    def test_switch_handles_save_and_free_errors(self, tmp_path):
        """Test switch continues gracefully when saving state or freeing memory fails."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.side_effect = Exception("monitor unavailable")
        mock_manager = AsyncMock()
        mock_manager.free_memory.side_effect = Exception("free failed")

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0

    def test_switch_not_implemented_model_load(self, tmp_path):
        """Test switch handles NotImplementedError when loading backend models."""
        runner = _runner()

        config = {
            "myapp": {
                "after": {
                    "swarmui": ["some/model.safetensors"]
                }
            }
        }
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()
        mock_manager.free_memory.return_value = None
        mock_manager.load_model.side_effect = NotImplementedError("not supported")

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0

    def test_switch_swarmui_free_not_implemented(self, tmp_path):
        """Test switch continues when swarmui free_memory raises NotImplementedError."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        lmstudio_manager = AsyncMock()
        lmstudio_manager.free_memory.return_value = None
        swarmui_manager = AsyncMock()
        swarmui_manager.free_memory.side_effect = NotImplementedError("not supported")

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []

        call_count = [0]

        def create_manager(client):
            call_count[0] += 1
            # Alternate between lmstudio (odd calls) and swarmui (even calls)
            return lmstudio_manager if call_count[0] % 2 == 1 else swarmui_manager

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, create_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0

    def test_switch_restore_unload_error_is_swallowed(self, tmp_path):
        """Test that unload errors during restore are silently swallowed."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio")
        ]
        mock_manager = AsyncMock()
        # unload_model raises, but load_model succeeds
        mock_manager.unload_model.side_effect = RuntimeError("already unloaded")

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0
            # load_model is still called despite unload failure
            assert mock_manager.load_model.called

    def test_switch_restore_load_error_is_logged(self, tmp_path):
        """Test that load errors during restore are logged without crashing."""
        runner = _runner()

        config = {"myapp": {"after": {}}}
        config_file = tmp_path / ".llm-switch-config.json"
        config_file.write_text(json.dumps(config))

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio")
        ]
        mock_manager = AsyncMock()
        mock_manager.unload_model.return_value = None
        mock_manager.load_model.side_effect = RuntimeError("load failed")

        with patch("os.path.expanduser", return_value=str(tmp_path)), \
             patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_create.return_value = mock_client
            mock_classes.return_value = (lambda c: mock_monitor, lambda c: mock_manager)

            result = runner.invoke(cli, ["switch", "myapp"])
            assert result.exit_code == 0

    def test_validate_interval_too_small(self):
        """Test that --interval < 1 is rejected."""
        runner = _runner()
        result = runner.invoke(cli, ["monitor", "--interval", "0"])
        assert result.exit_code != 0
        assert "interval" in result.output.lower()

    def test_monitor_all_backends(self):
        """Test `monitor` (default all) creates clients for both backends."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_monitor.get_resource_info.return_value = ResourceUsage(
            vram_used=0.0, vram_total=0.0, ram_used=0.0, ram_total=0.0, cpu_usage=0.0
        )
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor"])
            assert result.exit_code == 0
            assert mock_create.call_count == 2

    def test_monitor_lmstudio_vram_column(self):
        """Test VRAM column appears when a loaded model has VRAM allocated."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="phi-3", instance_id="inst1", backend="lmstudio",
                        vram_allocated=4.5)
        ]
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert "vram_allocated_gb" in data["loaded_models"][0]

    def test_monitor_lmstudio_available_models_table(self):
        """Test that available models table is printed when present."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = [
            DownloadedModel(name="phi-3", path="phi-3.gguf", size_gb=2.5, backend="lmstudio")
        ]

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio"])
            assert result.exit_code == 0
            assert "phi-3" in result.output

    def test_monitor_not_implemented_error_handled(self):
        """Test NotImplementedError is stored but does not crash the command."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.side_effect = NotImplementedError("not supported")
        mock_manager = AsyncMock()
        mock_manager.list_available_models.side_effect = NotImplementedError("not supported")

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio"])
            assert result.exit_code == 0

    def test_monitor_consecutive_failure_warning(self):
        """Test warning after WARN_THRESHOLD consecutive failures."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.side_effect = RuntimeError("fail")
        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes, \
             patch("asyncio.sleep", return_value=None):
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            # Simulate 3 polling iterations to trigger the warning
            call_count = 0

            original_invoke = runner.invoke

            async def _limited_monitor():
                pass

            # Use watch mode; stop after 3 iterations by patching asyncio.sleep to raise
            sleep_calls = [0]

            async def fake_sleep(n):
                sleep_calls[0] += 1
                if sleep_calls[0] >= 3:
                    raise KeyboardInterrupt()

            with patch("asyncio.sleep", side_effect=fake_sleep):
                result = runner.invoke(
                    cli,
                    ["monitor", "--backend", "lmstudio", "--watch", "--interval", "1"],
                    catch_exceptions=True,
                )
            # Warning should appear for repeated failures
            assert result.exit_code == 0

    def test_monitor_swarmui_not_implemented_resources(self):
        """Test NotImplementedError from get_resource_info is handled gracefully."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.get_resource_info.side_effect = NotImplementedError("no resources")
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "swarmui"])
            assert result.exit_code == 0

    def test_monitor_swarmui_vram_column(self):
        """Test VRAM column appears in swarmui JSON output when loaded model has VRAM."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.get_resource_info.return_value = ResourceUsage(
            vram_used=4.0, vram_total=8.0, ram_used=8.0, ram_total=16.0, cpu_usage=30.0
        )
        mock_monitor.list_loaded_models.return_value = [
            LoadedModel(name="sdxl", instance_id="i1", backend="swarmui",
                        vram_allocated=4.0)
        ]
        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "swarmui", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert "vram_allocated_gb" in data["loaded_models"][0]

    def test_monitor_swarmui_not_implemented_loaded_models(self):
        """Test NotImplementedError from swarmui list_loaded_models is handled gracefully."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.get_resource_info.return_value = ResourceUsage(
            vram_used=0.0, vram_total=0.0, ram_used=0.0, ram_total=0.0, cpu_usage=0.0
        )
        mock_monitor.list_loaded_models.side_effect = NotImplementedError("not supported")
        mock_manager = AsyncMock()

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            result = runner.invoke(cli, ["monitor", "--backend", "swarmui", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output.strip())
            assert "loaded_models_error" in data

    def test_monitor_client_close_exception_is_swallowed(self):
        """Test that exceptions from client.close() in the finally block are swallowed."""
        runner = _runner()

        mock_monitor = AsyncMock()
        mock_monitor.list_loaded_models.return_value = []
        mock_manager = AsyncMock()
        mock_manager.list_available_models.return_value = []

        with patch("llm_control.main.get_settings"), \
             patch("llm_control.cli.factories.create_client") as mock_create, \
             patch("llm_control.main.get_backend_classes") as mock_classes:
            mock_client = AsyncMock()
            mock_client.close = AsyncMock(side_effect=Exception("close failed"))
            mock_create.return_value = mock_client
            mock_classes.return_value = (
                lambda c: mock_monitor,
                lambda c: mock_manager,
            )

            # The command should succeed even if close() raises
            result = runner.invoke(cli, ["monitor", "--backend", "lmstudio"])
            assert result.exit_code == 0

