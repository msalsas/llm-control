"""Backend factory and registry — single extension point for new backends."""

from llm_control.services.interface import IBackendMonitor, IModelManager


# Registry — the single extension point for new backends
def _get_backend_classes() -> dict[str, tuple[type[IBackendMonitor], type[IModelManager]]]:
    """Return the registry dict. Defined here to avoid circular imports."""
    from llm_control.services.lmstudio.monitor import LmStudioMonitor as LSMonitor
    from llm_control.services.lmstudio.monitor import LmStudioManager as LSManager
    from llm_control.services.swarmui.monitor import SwarmUIMonitor as SUMonitor
    from llm_control.services.swarmui.monitor import SwarmUIManager as SUManager

    return {
        "lmstudio": (LSMonitor, LSManager),
        "swarmui": (SUMonitor, SUManager),
    }


def get_backend_classes(backend: str) -> tuple[type[IBackendMonitor], type[IModelManager]]:
    """Return (monitor_cls, manager_cls) for the given backend name."""
    registry = _get_backend_classes()
    if backend not in registry:
        raise ValueError(f"Unknown backend: {backend}")
    return registry[backend]


def create_client(settings: "Settings", backend: str) -> "LmStudioClient | SwarmUIClient":
    """Create the appropriate HTTP client based on backend name.

    Returns an async context manager (client instance).
    """
    if backend == "lmstudio":
        from llm_control.services.lmstudio.client import LmStudioClient
        return LmStudioClient(
            base_url=settings.lmstudio_base_url,
            token=settings.lmstudio_token,
            retry_intervals=tuple(settings.retry_intervals),
        )
    elif backend == "swarmui":
        from llm_control.services.swarmui.client import SwarmUIClient
        return SwarmUIClient(
            base_url=settings.swarmui_base_url,
            token=settings.swarmui_token,
            retry_intervals=tuple(settings.retry_intervals),
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def list_backends() -> list[str]:
    """Return available backend names."""
    return sorted(_get_backend_classes().keys())
