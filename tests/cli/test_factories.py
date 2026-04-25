"""Tests for CLI backend factory and registry."""

import pytest


class TestGetBackendClasses:
    """Test get_backend_classes() returns correct class pairs."""

    def test_lmstudio_returns_correct_classes(self):
        from llm_control.cli.factories import get_backend_classes
        monitor_cls, manager_cls = get_backend_classes("lmstudio")
        assert monitor_cls.__name__ == "LmStudioMonitor"
        assert manager_cls.__name__ == "LmStudioManager"

    def test_swarmui_returns_correct_classes(self):
        from llm_control.cli.factories import get_backend_classes
        monitor_cls, manager_cls = get_backend_classes("swarmui")
        assert monitor_cls.__name__ == "SwarmUIMonitor"
        assert manager_cls.__name__ == "SwarmUIManager"

    def test_unknown_backend_raises(self):
        from llm_control.cli.factories import get_backend_classes
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend_classes("unknown")


class TestListBackends:
    """Test list_backends() returns available backend names."""

    def test_returns_sorted_list(self):
        from llm_control.cli.factories import list_backends
        backends = list_backends()
        assert "lmstudio" in backends
        assert "swarmui" in backends
        # Should be sorted alphabetically
        assert backends == sorted(backends)

    def test_returns_exactly_two(self):
        from llm_control.cli.factories import list_backends
        assert len(list_backends()) == 2


class TestCreateClient:
    """Test create_client() returns correct client type."""

    @pytest.mark.asyncio
    async def test_create_lmstudio_client(self):
        from llm_control.cli.factories import create_client
        from llm_control.utils.config import Settings

        settings = Settings()
        client = create_client(settings, "lmstudio")
        assert client.__class__.__name__ == "LmStudioClient"
        await client.close()

    @pytest.mark.asyncio
    async def test_create_swarmui_client(self):
        from llm_control.cli.factories import create_client
        from llm_control.utils.config import Settings

        settings = Settings()
        client = create_client(settings, "swarmui")
        assert client.__class__.__name__ == "SwarmUIClient"
        await client.close()

    def test_unknown_backend_raises(self):
        from llm_control.cli.factories import create_client
        from llm_control.utils.config import Settings

        settings = Settings()
        with pytest.raises(ValueError, match="Unknown backend"):
            create_client(settings, "unknown")
