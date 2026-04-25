# llm-control — Project Plan

## Overview

A Python CLI tool to monitor and manage **LMStudio** (LLM inference) and **SwarmUI** (image generation with ComfyUI backends) on a remote Windows server. Uses SOLID principles, async HTTP clients, Pydantic models, pytest TDD, and click for the CLI.

---

## Architecture

```
┌─────────────────────────────────────┐
│           main.py (CLI)             │
│  ┌──────────┬──────────┬──────────┐ │
│  │ monitor  │ control  │ config   │ │
│  └──────────┴──────────┴──────────┘ │
├─────────────────────────────────────┤
│         src/ (core library)        │
│  ┌────────────┬──────────────────┐  │
│  │ models/    │  services/       │  │
│  │ (data)     │  (logic + APIs)  │  │
│  └────────────┴──────────────────┘  │
│  ┌────────────┐                     │
│  │ utils/     │                     │
│  │ (config,   │                     │
│  │ formatter) │                     │
│  └────────────┘                     │
├─────────────────────────────────────┤
│         tests/ (TDD suite)         │
│  All HTTP calls mocked.            │
└─────────────────────────────────────┘
```

---

## Project Structure

```
llm-control/
├── pyproject.toml                     # Dependencies, tool config
├── .env.example                       # Template for credentials
├── .venv/                             # Python virtual environment
│
├── src/
│   └── llm_control/                   # Python package (snake_case) — CLI binary is `llm-control`
│       ├── __init__.py
│       ├── main.py                    # CLI entry point (click commands, registered in pyproject.toml)
│       │
│       ├── models/                    # Pure data classes (value objects)
│       │   ├── __init__.py
│       │   ├── resource.py            # ResourceUsage: VRAM, RAM, CPU, GPU stats
│       │   ├── model_info.py          # LoadedModel, DownloadedModel
│       │   ├── backend_status.py      # BackendStatus, ServerStatus
│       │   └── connection.py          # ConnectionConfig (IP, port, optional auth)
│       │
│       ├── services/                  # Business logic + interfaces
│       │   ├── __init__.py
│       │   ├── interface.py           # IBackendMonitor, IModelManager protocols
│       │   │
│       │   ├── lmstudio/              # LMStudio service layer
│       │   │   ├── __init__.py
│       │   │   ├── client.py          # LmStudioClient — HTTP calls to LMStudio v1 REST API
│       │   │   └── monitor.py         # LmStudioMonitor + LmStudioManager (load/unload/free_memory)
│       │   │
│       │   └── swarmui/               # SwarmUI service layer
│       │       ├── __init__.py
│       │       ├── client.py          # SwarmUIClient — HTTP calls + session flow for SwarmUI API
│       │       └── monitor.py         # SwarmUIMonitor + SwarmUIManager (load/free_memory)
│       │
│       └── utils/                     # Cross-cutting concerns
│           ├── __init__.py
│           ├── config.py              # Settings class using pydantic-settings BaseSettings
│           └── formatter.py           # Table output / JSON output
│
├── tests/                             # TDD — all HTTP calls mocked
│   ├── __init__.py
│   │
│   ├── models/
│   │   ├── test_resource.py
│   │   ├── test_model_info.py
│   │   ├── test_backend_status.py
│   │   └── test_connection.py
│   │
│   ├── services/
│   │   ├── test_interface.py
│   │   ├── lmstudio/
│   │   │   ├── __init__.py
│   │   │   ├── test_client.py         # Mock HTTP, verify parsing of v1 endpoints
│   │   │   ├── test_monitor.py        # Monitor logic with mocked client
│   │   │   └── test_manager.py        # free_memory smart fallback + NotImplementedError
│   │   └── swarmui/
│   │       ├── __init__.py
│   │       ├── test_client.py         # Mock SwarmUI API responses, session flow
│   │       ├── test_monitor.py        # Monitor logic, resource parsing
│   │       └── test_manager.py        # load_model, free_memory, unload raises
│   │
│   ├── utils/
│   │   └── test_config.py             # Settings parsing, validation
│   │
│   └── test_formatter.py              # Table/JSON output formatting

├── src/llm_control/main.py            # CLI entry point (click commands)
└── README.md                          # Usage docs
```

---

## SOLID Design

### Interface Segregation — Narrow Protocols

```python
# src/services/interface.py
from typing import Protocol, AsyncIterator
from ..models.resource import ResourceUsage
from ..models.model_info import LoadedModel, DownloadedModel
from ..models.backend_status import ServerStatus

class IBackendMonitor(Protocol):
    """All monitors implement this. Some methods may raise NotImplementedError."""
    async def get_resource_info(self) -> ResourceUsage: ...  # SwarmUI only; LMStudio raises
    async def get_server_status(self) -> ServerStatus: ...   # SwarmUI only; LMStudio raises
    async def list_loaded_models(self) -> list[LoadedModel]: ...

class IModelManager(Protocol):
    """For load/unload/free-memory operations."""
    async def load_model(self, model_path: str) -> None: ...
    async def unload_model(self, instance_id: str) -> None: ...  # LMStudio only; SwarmUI raises
    async def list_available_models(self) -> list[DownloadedModel]: ...
    async def free_memory(self) -> None: ...                      # Both backends

class IClient(Protocol):
    """Low-level HTTP communication. Each backend handles its own session/auth internally."""
    async def get(self, path: str, **kwargs) -> dict: ...
    async def post(self, path: str, payload: dict) -> dict: ...
```

> **Interface notes:**
> - LMStudio does NOT have resource_info or server_status endpoints → those methods raise `NotImplementedError`
> - SwarmUI does NOT have per-model unload → `unload_model()` raises `NotImplementedError` (use `free_memory()` instead)
> - Each backend's client handles its own session/auth internally (SwarmUI sessions, LMStudio optional Bearer token)

### Dependency Inversion — DIP

- `main.py` depends on interfaces (`IBackendMonitor`, `IModelManager`)
- Concrete clients are injected at runtime via config
- New backends = new implementations of the protocols (no changes to main.py)

### Single Responsibility — SRP

| Class | Single Responsibility |
|---|---|
| `LmStudioClient` | HTTP communication with LMStudio v1 REST API only (optional Bearer token) |
| `SwarmUIClient` | HTTP + session flow for SwarmUI API only (auto-refreshes session per request) |
| `LmStudioMonitor` | Collects/transforms monitoring data from LMStudio only (loaded models + config, no VRAM stats) |
| `SwarmUIMonitor` | Collects/transforms monitoring data from SwarmUI only (VRAM/RAM/CPU + loaded models) |
| `ResourceUsage` | Pure value object — holds resource stats |
| `LoadedModel` | Pure value object — holds model info |
| `DownloadedModel` | Pure value object — holds downloaded model info |
| `ConnectionConfig` | Pure value object — holds connection params |
| `config.py` | Loads `.env` and builds `ConnectionConfig` |
| `formatter.py` | Formats output as table or JSON |

---

## API Integration Map

### LMStudio (v1 REST API — `http://ip:1234`)

| Method | Endpoint | HTTP | Returns |
|---|---|---|---|
| `list_models()` | `/api/v1/models` | GET | DownloadedModel[] + loaded_instances per model |
| `load_model(model, **opts)` | `/api/v1/models/load` | POST | `{ type, instance_id, load_time_seconds, status }` |
| `unload_model(instance_id)` | `/api/v1/models/unload` | POST | `{ instance_id }` |

> **LMStudio resource monitoring** — The v1 REST API does NOT expose per-model VRAM/RAM/CPU stats.
> Only SwarmUI provides this via `/API/GetServerResourceInfo`. For LMStudio, we show:
> - Model config (context_length, parallel, flash_attention, etc.) from `loaded_instances` in list response
> - No VRAM/RAM/CPU breakdown — only SwarmUI has resource telemetry

### SwarmUI (v0.9.x)

| Method | Endpoint | HTTP | Returns |
|---|---|---|---|
| `get_session()` | `/API/GetNewSession` | POST | session_id |
| `get_resource_info()` | `/API/GetServerResourceInfo` | POST | ResourceUsage (CPU, RAM, GPU VRAM) |
| `get_server_status()` | `/API/GetGlobalStatus` | POST | ServerStatus |
| `list_loaded_models()` | `/API/ListLoadedModels` | POST | LoadedModel[] |
| `list_available_models()` | `/API/ListModels` | POST | DownloadedModel[] |
| `load_model(path)` | `/API/SelectModel` | POST | success/error |
| `free_memory()` | `/API/FreeBackendMemory` | POST | success/error |

> **SwarmUI model management** — No per-model unload endpoint exists. The only option is
> `FreeBackendMemory` which clears ALL loaded models from all backends. This is acceptable:
> clearing all VRAM/RAM at once is fine for the user's use case (no need for precise control).

---

## CLI Commands

```bash
# Monitoring (default: human-readable table; --json for JSON output)
llm-control monitor --backend lmstudio
llm-control monitor --backend swarmui
llm-control monitor --all
llm-control monitor --watch --interval 30    # continuous polling

# Model management — LMStudio (full per-model control)
llm-control models list --backend lmstudio
llm-control load   --backend lmstudio --model "microsoft/Phi-3-mini"
llm-control unload --backend lmstudio --model "microsoft/Phi-3-mini"

# Model management — SwarmUI (load only; no per-model unload)
llm-control models list --backend swarmui
llm-control load   --backend swarmui --model "path/to/model.safetensors"

# Free memory — works on both backends
llm-control free-memory --backend lmstudio    # smart fallback: lists loaded → unloads each one
llm-control free-memory --backend swarmui     # clears ALL models from ALL backends (only option available)

# Diagnostics
llm-control status                           # quick health check
```

> **Command separation:** `unload` is LMStudio-only (per-model control). If you run
> `unload --backend swarmui`, the CLI shows a friendly error: "SwarmUI doesn't support
> per-model unload. Use `free-memory` instead." This keeps commands explicit and avoids
> confusion since SwarmUI's only option clears ALL loaded models at once.

---

## Installation & CLI Entry Point

The tool is installed via pip and invoked as a standalone CLI binary:
```bash
pip install -e .
llm-control monitor --backend lmstudio
```

`pyproject.toml` will include the entry point registration:
```toml
[project.scripts]
llm-control = "llm_control.main:cli"
```

This means `main.py` lives inside the `src/llm_control/` package and exposes a `cli()` function that click uses as the CLI entry point. The package name is `llm_control` (snake_case), matching the CLI binary name `llm-control`.

---

## Dependencies (`pyproject.toml`)

```toml
[project]
name = "llm-control"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "click>=8.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "respx>=0.4"]

[project.scripts]
llm-control = "llm_control.main:cli"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

> **Note:** `pydantic-settings` replaces plain python-dotenv (following the ai-influencer pattern).
> `respx` is used for HTTP mocking in tests (cleaner than pytest-mock + httpx MockTransport).
> Package name uses snake_case (`llm_control`) while CLI binary uses kebab-case (`llm-control`).

---

## Environment Variables (`.env.example`)

```bash
# LMStudio — full URL format (no auth required)
LMSTUDIO_BASE_URL=http://192.168.x.x:1234

# SwarmUI — full URL format, token is optional (not used by default)
SWARMUI_BASE_URL=http://192.168.x.x:7801
SWARMUI_TOKEN=your_swarm_auth_token   # only if auth is enabled on your instance

# Polling (for --watch mode)
POLL_INTERVAL=30
```

---

## TDD Test Strategy

All tests use **respx** for HTTP mocking — no live servers needed.

| Test File | What It Tests | Mock Target |
|---|---|---|
| `tests/test_config.py` | Settings parsing, required fields, defaults | N/A (pure logic) |
| `tests/models/test_connection.py` | ConnectionConfig validation | N/A (Pydantic model) |
| `tests/models/test_resource.py` | Resource calculation methods | N/A (value object) |
| `tests/models/test_model_info.py` | Model info construction | N/A (value object) |
| `tests/models/test_backend_status.py` | Status aggregation logic | N/A (value object) |
| `tests/services/test_interface.py` | Protocol compliance + NotImplementedError cases | N/A (protocol check) |
| `tests/services/lmstudio/test_client.py` | HTTP calls to LMStudio v1, response parsing | respx mock |
| `tests/services/lmstudio/test_monitor.py` | Monitor data transformation from `/api/v1/models` | LmStudioClient mock |
| `tests/services/lmstudio/test_manager.py` | free_memory smart fallback: list loaded → unload each | LmStudioClient mock |
| `tests/services/swarmui/test_client.py` | Session flow + all SwarmUI API routes | respx mock |
| `tests/services/swarmui/test_monitor.py` | Monitor logic, resource parsing from `/API/GetServerResourceInfo` | SwarmUIClient mock |
| `tests/services/swarmui/test_manager.py` | load_model success, free_memory calls FreeBackendMemory, unload_model raises | SwarmUIClient mock |
| `tests/test_formatter.py` | Table/JSON output formatting | N/A (pure function) |

### Retry / Backoff Pattern (from ai-influencer reference)

Both backends use a retry strategy with configurable backoff intervals:
- **Long-running services** (LMStudio/SwarmUI): `(60, 180, 300)` seconds — designed for "server is down/restarting" scenarios
- Tests verify: (a) success on first attempt, (b) success after transient failure, (c) raises after all retries exhausted

---

## Implementation Phases (TDD Order)

Each phase follows: **write tests → implement code → verify all pass**.

### Phase 1 — Skeleton & Config ✅ COMPLETE

**Files created:**
- `pyproject.toml` (with `[project.scripts] = "llm-control" = "llm_control.main:cli"`)
- `.env.example`
- `src/llm_control/__init__.py`, `src/llm_control/models/__init__.py`, etc.
- `tests/__init__.py`, `tests/models/__init__.py`, etc.

**Implementation:**
- `src/llm_control/utils/config.py` — Settings class using `pydantic-settings` BaseSettings (matches ai-influencer pattern)
- `src/llm_control/models/connection.py` — `ConnectionConfig` (Pydantic model for connection params)

**Tests:**
- `tests/utils/test_config.py` — parse .env, validate required fields, handle missing values ✅
- `tests/models/test_connection.py` — ConnectionConfig construction, validation errors ✅

### Phase 2 — Data Models ✅ COMPLETE

**Implementation:**
- `src/llm_control/models/resource.py` — `ResourceUsage` (VRAM, RAM, CPU, GPU stats) + `GPUStats`
- `src/llm_control/models/model_info.py` — `LoadedModel`, `DownloadedModel`
- `src/llm_control/models/backend_status.py` — `BackendStatus`, `ServerStatus`

**Tests:**
- `tests/models/test_resource.py` — construction, serialization, validation ✅
- `tests/models/test_model_info.py` — construction from API responses ✅
- `tests/models/test_backend_status.py` — status aggregation logic ✅

### Phase 3 — LMStudio Service ✅ COMPLETE

**Implementation:**
- `src/llm_control/services/interface.py` — define protocols (`IBackendMonitor`, `IModelManager`)
- `src/llm_control/services/lmstudio/client.py` — `LmStudioClient` (HTTP calls with retry/backoff, optional Bearer token)
- `src/llm_control/services/lmstudio/monitor.py` — `LmStudioMonitor` + `LmStudioManager`
  - Monitor: lists loaded models + config from `/api/v1/models` response (`loaded_instances`)
  - Manager: load/unload via v1 endpoints, free_memory smart fallback (list loaded → unload each)
  - Resource info / server status raise `NotImplementedError` (LMStudio has no telemetry endpoints)

**Tests:**
- `tests/services/test_interface.py` — protocol compliance + NotImplementedError tests ✅
- `tests/services/lmstudio/test_client.py` — mock HTTP (respx), verify parsing of `/api/v1/models`, load/unload responses ✅
- `tests/services/lmstudio/test_monitor.py` — monitor logic with mocked client, retry/backoff tests ✅
- `tests/services/lmstudio/test_manager.py` — free_memory smart fallback: list loaded → unload each one ✅

### Phase 4 — SwarmUI Service ✅ COMPLETE

**Implementation:**
- `src/llm_control/services/swarmui/client.py` — `SwarmUIClient` (session flow + all API routes, follows ai-influencer pattern)
  - Every request requires a fresh session from `GetNewSession` (auto-refreshed internally by client)
  - Retry/backoff on transient failures
- `src/llm_control/services/swarmui/monitor.py` — `SwarmUIMonitor` + memory clearing
  - Monitor: resource info, server status, loaded models from SwarmUI endpoints
  - Manager: load via SelectModel, free_memory via FreeBackendMemory (unload_model raises NotImplementedError)

**Tests:**
- `tests/services/swarmui/test_client.py` — mock SwarmUI API responses, verify session flow, resource parsing (respx mocks) ✅
- `tests/services/swarmui/test_monitor.py` — monitor logic, memory clearing tests (mock client) ✅
- `tests/services/swarmui/test_manager.py` — load_model success, free_memory calls FreeBackendMemory, unload_model raises NotImplementedError ✅

### Phase 5 — CLI Integration ✅ COMPLETE

**Implementation:**
- `src/llm_control/main.py` — click subcommands: `monitor`, `models`, `load`, `unload`, `free-memory`, `status`, `--watch`, `--json`
  - `unload --backend swarmui` → shows error: "SwarmUI doesn't support per-model unload. Use `free-memory` instead."
  - `free-memory --backend lmstudio` → calls LmStudioManager.free_memory() (smart fallback)
  - `free-memory --backend swarmui` → calls SwarmUIManager.free_memory() (direct FreeBackendMemory call)

**Tests:**
- All unit tests pass (54 tests, 0 failures) ✅

### Phase 6 — Polish ✅ COMPLETE

- Error handling: try/except around asyncio.run(), ClickException for user-facing errors ✅
- Output formatting: table default + `--json` flag working correctly ✅
- README.md documentation added ✅
- Logging configuration added ✅
- conftest.py for proper test path handling ✅

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| HTTP client | `httpx` with async | Modern, clean API; follows ai-influencer pattern |
| CLI framework | `click` | Clean subcommand structure, better UX than argparse |
| Data validation | Pydantic + pydantic-settings | Built-in serialization, `.env` loading via BaseSettings |
| Async | Yes (asyncio) | Enables `--watch` mode naturally; HTTP calls are I/O bound |
| Output format | Table default + `--json` flag | Human-friendly by default, machine-parseable when needed |
| Test mocking | `respx` for HTTP mocks | Clean httpx integration; follows ai-influencer pattern |
| Retry/backoff | Configurable intervals `(60, 180, 300)` | Handles "server is down/restarting" scenarios |
| SwarmUI unload | Clear-all (acceptable) | No per-model endpoint exists; clearing all VRAM/RAM at once is fine for user's use case |
| Auth tokens | Optional for both backends | Neither LMStudio nor SwarmUI require auth by default; token fields are optional in config |
| free-memory (LMStudio) | Smart fallback: list loaded → unload each one | No native "free all" endpoint exists, but chaining per-model unloads achieves the same result |
| LMStudio resource monitoring | Not available — raises NotImplementedError | v1 REST API has no VRAM/RAM/CPU telemetry; only SwarmUI provides this via `/API/GetServerResourceInfo` |
| Session management | Each client handles internally | SwarmUIClient auto-refreshes session per request; LmStudioClient optionally adds Bearer token header |
| Unsupported operations | Raise `NotImplementedError` with clear message | LMStudioMonitor raises on resource_info/server_status; SwarmUIMonitor raises on unload_model |

---

## Reference: ai-influencer SwarmUI Usage Patterns

The existing project at `/home/manolo/ai-influencer` demonstrates real SwarmUI usage:

- **Session flow**: Every request requires a fresh session from `POST /API/GetNewSession` (line 17 of `image_gen.py`)
- **Generation payload**: `{ "session_id": "...", "images": 1, "model": "...", "prompt": "...", "width": ..., "height": ... }` (lines 37-44)
- **Image download**: Separate `GET /View/...` call after generation succeeds (line 67-85)
- **Retry strategy**: `(60, 180, 300)` second backoff for transient failures (from `config/retries.py`)
- **HTTP client**: Direct `httpx.AsyncClient`, injected for testability (`image_gen.py` line 34)
- **No model management APIs used**: The project only uses `GetNewSession` + `GenerateText2Image` — confirming that SwarmUI's API is primarily for generation, not model lifecycle control.

---

## Code Review Improvements (Post-Implementation Audit)

All issues below have been identified and addressed in the implementation.

### Critical Fixes Applied

| # | Issue | Fix Applied |
|---|---|---|
| 1 | HTTP client resource leaks — clients never closed | Added `finally` blocks calling `await client.close()` on every CLI command; monitor loop closes clients after watch mode exits |
| 2 | Retry intervals too long (5.5 min per request) | Reduced to `(1, 2, 5)` seconds for CLI interactivity; made configurable via `Settings.retry_intervals` |
| 3 | No input validation on `--interval` | Added `min=1` constraint: `type=int, default=30, min=1` |
| 4 | Silent exception swallowing in watch mode | Track consecutive failures per backend; warn after 3 consecutive failures with `[WARN] Backend X failed 3 times consecutively` |
| 5 | Misleading `data` variable types | Split into separate typed dicts per backend (`lmstudio_data`, `swarmui_data`) instead of one reused variable |

### Important Fixes Applied

| # | Issue | Fix Applied |
|---|---|---|
| 6 | SwarmUI session refreshed on every request | Reuse existing session until error indicates invalidity; only call `_get_session()` when needed |
| 7 | Redundant `url` properties in Settings | Removed `lmstudio_url` and `swarmui_url` properties — use `lmstudio_base_url` / `swarmui_base_url` directly |
| 8 | Fragile `.env` path (relative, silently ignored) | Use `SettingsConfigDict(env_file=".env", extra="ignore")`; add fallback to env vars; no error if file missing (by design for dev flexibility) |
| 9 | Inconsistent error handling between backends | Both `free_memory()` implementations now catch and log individual errors without raising |
| 10 | No `--backend` filter on `status` command | Added `--backend` option to status: `llm-control status --backend lmstudio` |

### Nice-to-Have Fixes Applied

| # | Issue | Fix Applied |
|---|---|---|
| 11 | Hardcoded retry intervals not configurable | Added `retry_intervals: tuple[int, ...] = (1, 2, 5)` to Settings; clients read from settings |
| 12 | No CLI version flag | Added `@click.version_option(version="0.1.0", prog_name="llm-control")` |
| 13 | No graceful shutdown message in watch mode | Print `"Exiting..."` on KeyboardInterrupt; close HTTP clients before exit |
| 14 | Duplicate parsing logic across monitors | Created `_parse_model_list()` utility function shared by both monitors |
| 15 | No `.gitignore` for Python artifacts | Added top-level `.gitignore` excluding `__pycache__/`, `.pytest_cache/`, `.venv/`, `.env`, `*.egg-info/` |
| 16 | Unused import in interface.py | Removed unused `AsyncIterator` import from `typing` |

---

## GitHub Configuration (`.github/`)

```
.github/
├── CONTRIBUTING.md          # How to contribute: setup, tests, PR guidelines
└── CODEOWNERS               # Route review requests to appropriate reviewers
```

### Contributing Guidelines (`CONTRIBUTING.md`)

1. **Setup**: `pip install -e ".[dev]"` from project root
2. **Tests**: All HTTP calls mocked with `respx`; run `pytest tests/ -v`
3. **TDD workflow**: Write failing test first, then implement code
4. **PR requirements**: Must pass all 54+ tests; include new tests for any changes

### Code Owners (`CODEOWNERS`)

```
# All files owned by project maintainers
*       @maintainers
```

---

## Updated Key Design Decisions

| Decision | Original Choice | Updated Choice | Rationale |
|---|---|---|---|
| Retry/backoff | `(60, 180, 300)` seconds | `(1, 2, 5)` seconds + configurable | CLI needs fast feedback; server-down scenarios handled by retry count |
| Session management | Refresh every request | Reuse until invalidity | Reduces unnecessary API calls; servers track sessions more efficiently |
| `.env` loading | Relative path `.env` only | Relative path with env var fallback | Works from any CWD; respects `os.environ` for containerized deployments |
| Resource cleanup | No client lifecycle management | `finally` blocks close clients | Prevents resource leaks in long-running watch mode and batch operations |

---

## Implementation Phases (TDD Order) — Updated

### Phase 7 — Code Review Fixes ✅ COMPLETE (All Issues Resolved)

**Critical fixes applied:**
- HTTP client resource cleanup with `finally` blocks and async context managers (`__aenter__/__aexit__`)
- Reduced retry intervals: `(1, 2, 5)` seconds + configurable via Settings.retry_intervals
- Input validation on CLI options (interval callback validates >= 1)
- Consecutive failure tracking in watch mode (warns after 3 failures per backend)

**Important fixes applied:**
- SwarmUI session reuse until invalidity (removed per-request refresh waste)
- Removed redundant `url` properties from Settings (use base_url directly)
- Consistent error handling across both backends (both catch and log errors in free_memory)
- Added `--backend` filter to status command

**Nice-to-have fixes applied:**
- CLI version flag (`@click.version_option`)
- Graceful shutdown message ("Exiting...") + client cleanup on KeyboardInterrupt
- Shared `_parse_model_list()` utility function used by both monitors
- Top-level `.gitignore` excluding Python artifacts, venvs, secrets
- Removed unused `AsyncIterator` import from interface.py

**New files created:**
- `.github/CONTRIBUTING.md` — contribution guidelines (setup, tests, PR workflow)
- `.github/CODEOWNERS` — review routing to maintainers
- `.gitignore` — exclude Python build artifacts and secrets

**Test results: 53 passed, 0 failures**
