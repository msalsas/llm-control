# llm-control

A Python CLI tool to monitor and manage **LMStudio** (LLM inference) and **SwarmUI** (image generation with ComfyUI backends) on remote servers. Provides real-time resource tracking, model lifecycle management, and health diagnostics through a clean command-line interface.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-0A96u4.svg?style=flat)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **Monitor** backend status, resource usage (VRAM/RAM/CPU), and loaded models in real-time
- **Load/Unload** models on LMStudio; load models on SwarmUI
- **Free memory** across all backends with a single command
- **Watch mode** for continuous polling with configurable intervals
- **JSON output** for machine-parseable results and scripting integration
- **Health diagnostics** with quick status checks of all configured backends

## Installation

```bash
# Install from source (development mode)
pip install -e .

# Or install with dev dependencies for testing
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- Network access to LMStudio (`:1234`) and/or SwarmUI (`:7801`) instances

## Quick Start

```bash
# Monitor a specific backend
llm-control monitor --backend lmstudio
llm-control monitor --backend swarmui

# Continuous polling mode (every 30 seconds)
llm-control monitor --watch --interval 30

# Check health of all backends
llm-control status

# List available models
llm-control models --backend lmstudio
```

## Configuration

Create a `.env` file in the project root:

```ini
# LMStudio — full URL format (no auth required by default)
LMSTUDIO_BASE_URL=http://192.168.x.x:1234

# SwarmUI — full URL format, token is optional
SWARMUI_BASE_URL=http://192.168.x.x:7801
SWARMUI_TOKEN=your_swarm_auth_token   # only if auth is enabled on your instance

# Polling (for --watch mode)
POLL_INTERVAL=30

# Retry intervals (comma-separated, in seconds)
RETRY_INTERVALS=1, 2, 5
```

A template file `.env.example` is included for reference. Copy it to `.env` and fill in your values:

```bash
cp .env.example .env
```

## Usage

### Monitoring

```bash
# Monitor a specific backend (human-readable table output)
llm-control monitor --backend lmstudio
llm-control monitor --backend swarmui
llm-control monitor --all          # default; checks both backends

# Continuous polling mode
llm-control monitor --watch --interval 30

# JSON output for scripting / CI pipelines
llm-control monitor --backend swarmui --json
```

### Model Management

```bash
# List available models
llm-control models --backend lmstudio
llm-control models --backend swarmui

# Load a model
llm-control load --backend lmstudio --model "microsoft/Phi-3-mini"
llm-control load --backend swarmui --model "path/to/model.safetensors"

# Unload a model (LMStudio only — SwarmUI uses free-memory instead)
llm-control unload --backend lmstudio --model "inst1"

# Free all memory
llm-control free-memory --backend lmstudio    # unloads each loaded model individually
llm-control free-memory --backend swarmui     # clears ALL models from ALL backends
```

### Diagnostics

```bash
# Quick health check of all backends
llm-control status

# Check only a specific backend
llm-control status --backend lmstudio

# JSON output for diagnostics
llm-control status --json
```

## Backend Differences

| Feature | LMStudio | SwarmUI |
|---|---|---|
| Resource monitoring (VRAM/RAM/CPU) | Not available | Available via `/API/GetServerResourceInfo` |
| Per-model unload | Supported via v1 REST API | Not supported — use `free-memory` instead |
| Model loading | Via `POST /api/v1/models/load` | Via `POST /API/SelectModel` |
| Session management | None required | Required (auto-managed by client) |
| Resource telemetry | No VRAM/RAM/CPU endpoints | Full GPU stats including temperature & utilization |

## Architecture

```
llm-control/
├── src/llm_control/          # Core library package
│   ├── main.py               # CLI entry point (click commands)
│   ├── models/               # Pydantic data models
│   │   ├── resource.py       # ResourceUsage, GPUStats
│   │   ├── model_info.py     # LoadedModel, DownloadedModel
│   │   └── backend_status.py # BackendStatus, ServerStatus
│   ├── services/             # Business logic + API clients
│   │   ├── interface.py      # IBackendMonitor, IModelManager protocols
│   │   ├── lmstudio/         # LMStudio service layer
│   │   │   ├── client.py     # LmStudioClient (HTTP with retry/backoff)
│   │   │   └── monitor.py    # LmStudioMonitor + LmStudioManager
│   │   └── swarmui/          # SwarmUI service layer
│   │       ├── client.py     # SwarmUIClient (session flow + API routes)
│   │       └── monitor.py    # SwarmUIMonitor + SwarmUIManager
│   └── utils/                # Cross-cutting concerns
│       ├── config.py         # Settings via pydantic-settings
│       └── formatter.py      # Table + JSON output formatting
├── tests/                    # pytest TDD suite (all HTTP mocked)
├── .github/                  # GitHub configuration
│   ├── CONTRIBUTING.md       # How to contribute
│   └── CODEOWNERS            # Review routing
├── pyproject.toml            # Dependencies, tool config, entry point
└── .env.example              # Template for credentials
```

## Development

### Setup

```bash
# Clone and install
git clone https://github.com/your-org/llm-control.git
cd llm-control
pip install -e ".[dev]"
```

### Running Tests

All HTTP calls are mocked using `respx` — no live servers needed:

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src/llm_control --cov-report=html

# Run only model tests
pytest tests/models/ -v
```

### TDD Workflow

This project follows Test-Driven Development:

1. **Write a failing test** — documents expected behavior
2. **Implement the code** — make the test pass
3. **Verify all tests pass** — `pytest tests/ -v` should show 0 failures

## Design Principles

| Principle | Implementation |
|---|---|
| **SOLID** | Interface segregation via protocols; dependency injection at CLI layer |
| **Single Responsibility** | Each class handles one concern (HTTP, monitoring, management) |
| **Async I/O** | `asyncio` for efficient HTTP calls; enables `--watch` mode naturally |
| **Type Safety** | Pydantic models with runtime validation and serialization |
| **Mockable Tests** | All HTTP mocked with `respx`; no live servers needed in CI |

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| HTTP client | `httpx` with async | Modern, clean API; excellent async support |
| CLI framework | `click` | Clean subcommand structure; better UX than argparse |
| Data validation | Pydantic + pydantic-settings | Built-in serialization; `.env` loading via BaseSettings |
| Test mocking | `respx` for HTTP mocks | Clean httpx integration; no manual transport setup |
| Retry/backoff | Configurable `(1, 2, 5)` seconds | Fast feedback for CLI; handles transient failures |
| SwarmUI unload | Clear-all only | No per-model endpoint exists; clearing all VRAM/RAM is acceptable |
| Auth tokens | Optional for both backends | Neither requires auth by default; token fields are optional in config |

## Development Model Reference

This project was developed using the following AI model:

- **Model**: [Qwen3.6-35B-A3B](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF?show_file_info=Qwen3.6-35B-A3B-UD-IQ2_M.gguf)
- **Provider**: Unsloth (quantized GGUF format)

## License

This project is licensed under the [MIT License](LICENSE).

---

*Built with Python, httpx, Pydantic, Click, and pytest.*
