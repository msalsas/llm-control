"""Pytest configuration — adds src/ to sys.path for imports."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path so that `llm_control` is importable
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

# Force deterministic defaults regardless of user .env files
os.environ.setdefault("LMSTUDIO_BASE_URL", "http://localhost:1234")
os.environ.setdefault("SWARMUI_BASE_URL", "http://localhost:7801")
