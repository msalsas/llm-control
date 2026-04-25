# Contributing to llm-control

Thank you for your interest in contributing to llm-control! This guide covers setup, testing, and PR guidelines.

## Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd llm-control

# Create virtual environment (Python 3.10+)
python -m venv .venv
source .venv/bin/activate

# Install package with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

All HTTP calls are mocked using `respx` — no live servers needed:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src/llm_control --cov-report=html
```

The test suite follows TDD principles. When adding features or fixing bugs:

1. **Write a failing test first** — this documents the expected behavior
2. **Implement the fix** — make the test pass
3. **Verify all tests pass** — `pytest tests/ -v` should show 0 failures

## Code Style

- Follow PEP 8 with type annotations where practical
- Use docstrings for public functions and classes
- Keep functions focused on a single responsibility (SRP)
- Prefer explicit over implicit (e.g., use `dict | None` instead of bare `None`)

## Pull Request Guidelines

1. **Branch from `main`** — create a feature branch for your changes
2. **Include tests** — all new code must have corresponding test coverage
3. **Update the plan** — if you change architecture, update `.opencode/plans/project.md`
4. **Describe the change** — explain *why* in the PR description, not just *what*

## Architecture Notes

- `src/llm_control/` — core library (package)
- `tests/` — pytest suite (all HTTP mocked with respx)
- SOLID principles: protocols for interfaces, dependency injection, single responsibility
- Async I/O via asyncio; enables `--watch` mode naturally
- Pydantic models for data validation and serialization

## Getting Help

- Check existing issues before opening a new one
- Ask questions in discussions — no question is too basic
