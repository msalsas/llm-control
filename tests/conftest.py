"""Pytest configuration — adds src/ to sys.path for imports."""

import sys
from pathlib import Path

# Add the src directory to the Python path so that `llm_control` is importable
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)
