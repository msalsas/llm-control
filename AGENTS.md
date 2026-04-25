# AGENTS Guidelines for This Repository

This repository is a Python CLI tool (`llm-control`) that monitors and manages LMStudio and SwarmUI backends. When working on this project with an AI coding agent, follow the guidelines below to ensure smooth development and reliable test results.

## 1. Development Environment Setup

### Virtual Environment

Always use the virtual environment for running code:

```bash
# Create venv (if not already done)
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# or: .venv\Scripts\activate   # Windows

# Install package with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

All HTTP calls are mocked using `respx` — no live servers needed. Run tests from the project root:

```bash
# Run all tests (fast, ~1 second)
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src/llm_control --cov-report=html

# Run only specific test files
pytest tests/services/lmstudio/ -v
pytest tests/models/test_resource.py -v
```

### Running the CLI

```bash
# Via module invocation (no install needed)
python -m llm_control.main --help

# After pip install -e .
llm-control --help
```

## 2. Coding Conventions

### Import Style

- Use absolute imports from `llm_control.*` throughout the codebase (not relative imports like `..models`)
- The `tests/conftest.py` adds `src/` to `sys.path` so `from llm_control.models import ...` works in tests
- Do not use relative imports (`from ..models import X`) — they break when pytest runs from the project root

### Type Annotations

- Use Python 3.10+ syntax: `str | None`, `list[str]`, `dict[str, Any]` instead of `Optional[str]`, `List[str]`
- Annotate function signatures where practical; avoid bare `None` in parameter defaults (use `= None`)

### Error Handling

- Use `click.ClickException` for user-facing errors in CLI commands
- Log warnings with `logger.warning()` for recoverable failures
- Raise `NotImplementedError` with clear messages for unsupported operations (documented per backend)

### Async Patterns

- All HTTP clients use `httpx.AsyncClient`; never mix sync/async calls
- Use async context managers (`async with`) for client lifecycle: `async with await create_client(settings) as client:`
- Always close clients in `finally` blocks or via `__aexit__` to prevent resource leaks

### Code Structure

- Keep each class focused on a single responsibility (SRP)
- Use protocols (`IBackendMonitor`, `IModelManager`) for interface definitions
- Shared utilities go in `src/llm_control/utils/formatter.py` (e.g., `_parse_model_list()`)

## 3. Testing Workflow

### TDD Order

1. **Write a failing test** — documents expected behavior before implementation
2. **Implement the code** — make the test pass
3. **Verify all tests pass** — `pytest tests/ -v` should show 0 failures

### Test File Conventions

| Directory | What It Tests | Mock Strategy |
|---|---|---|
| `tests/models/` | Pydantic data models | No mocking needed (pure value objects) |
| `tests/services/lmstudio/` | LMStudio HTTP client, monitor, manager | `respx` for HTTP mocks; `AsyncMock` for service layer |
| `tests/services/swarmui/` | SwarmUI HTTP client, monitor, manager | `respx` for session/API mocks; `AsyncMock` for service layer |
| `tests/utils/` | Settings parsing, formatting utilities | No mocking needed (pure logic) |

### Adding New Tests

- Place tests in the matching directory under `tests/` (e.g., new model → `tests/models/test_xxx.py`)
- Use `@pytest.mark.asyncio` for async test methods
- Mock HTTP responses with `respx.mock`; never make real network calls in tests

## 4. Project-Specific Notes

### Backend Differences Matter

LMStudio and SwarmUI have fundamentally different capabilities:

- **LMStudio**: No resource telemetry (VRAM/RAM/CPU); supports per-model unload; uses v1 REST API
- **SwarmUI**: Full resource monitoring; no per-model unload (use `free-memory` instead); requires session management

When implementing features, check which backend is being targeted and handle unsupported operations with clear `NotImplementedError` messages.

### Retry Configuration

Retry intervals are configurable via `Settings.retry_intervals`. Default is `(1, 2, 5)` seconds for CLI interactivity. Do not hardcode retry values in clients — always read from settings.

### Session Management (SwarmUI)

The SwarmUI client reuses sessions until the server rejects them. Never force a session refresh on every request — only refresh when an error indicates invalidity (`self._session_id = None`).

## 5. Useful Commands Recap

| Command | Purpose |
|---|---|
| `pytest tests/ -v` | Run all tests with verbose output |
| `pytest tests/ --cov=src/llm_control` | Run tests with coverage report |
| `python -m llm_control.main --help` | Show CLI help (no install needed) |
| `pip install -e ".[dev]"` | Install package + dev dependencies |
| `llm-control monitor --backend lmstudio` | Quick smoke test of the CLI |

## 6. CI / GitHub Actions

This project uses `.github/workflows/pytest.yml` for continuous integration:

- Runs on every push and pull request
- Tests against Python 3.10, 3.11, 3.12
- Uses `pip install -e ".[dev]"` then `pytest tests/ -v --tb=short`
- Caches the virtual environment between runs for speed

---

Following these practices ensures that agent-assisted development stays fast and reliable. When in doubt, run `pytest tests/ -v` to verify your changes don't break existing functionality.
