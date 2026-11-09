"""Paths and constants."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
# Overridable so the app can serve an alternate problem set (e.g. a demo set for screenshots).
PROBLEMS_DIR = Path(os.environ.get("SWE_PRAC_PROBLEMS", ROOT / "problems"))
REFERENCE_DIR = Path(os.environ.get("SWE_PRAC_REFERENCE", ROOT / "reference"))
STATIC_DIR = PACKAGE_DIR / "static"
RUNNER_PATH = PACKAGE_DIR / "runner.py"
USER_RUFF_CONFIG = PACKAGE_DIR / "user_ruff.toml"

DATA_DIR = Path(os.environ.get("SWE_PRAC_DATA", ROOT / "data"))

# The interpreter running the app (the project venv) also runs user code and ruff.
PYTHON = sys.executable

TIME_LIMIT_SECONDS = 90 * 60
# Cumulative pacing targets from the source doc: L1 by 15 min, L2 by 35, L3 by 60, L4 by 85.
PACING_SECONDS = {1: 15 * 60, 2: 35 * 60, 3: 60 * 60, 4: 85 * 60}
LEVELS = (1, 2, 3, 4)

RUN_TIMEOUT_SECONDS = 10
SCRATCH_TIMEOUT_SECONDS = 10
MAX_SCRATCH_OUTPUT = 50_000
