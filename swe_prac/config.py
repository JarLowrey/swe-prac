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
DESIGNS_DIR = Path(os.environ.get("SWE_PRAC_DESIGNS", ROOT / "designs"))
ALGO_DIR = Path(os.environ.get("SWE_PRAC_ALGO", ROOT / "algorithms"))
TECH_DIR = Path(os.environ.get("SWE_PRAC_TECH", ROOT / "tech"))
STATIC_DIR = PACKAGE_DIR / "static"
RUNNER_PATH = PACKAGE_DIR / "runner.py"
# helpers.py beside scratch.py in an algorithms session: builds lists, trees and graphs.
SCRATCH_HELPERS_PATH = PACKAGE_DIR / "scratch_helpers.py"
USER_RUFF_CONFIG = PACKAGE_DIR / "user_ruff.toml"
ALGO_RUFF_CONFIG = PACKAGE_DIR / "user_ruff_algo.toml"  # user_ruff.toml minus camelCase checks

# The interpreter that runs the build tools (the project venv) also runs their checks of each
# problem's reference solution through the runner, and ruff (execution.py).
PYTHON = sys.executable

TIME_LIMIT_SECONDS = 90 * 60
# Cumulative pacing targets from the source doc: L1 by 15 min, L2 by 35, L3 by 60, L4 by 85.
PACING_SECONDS = {1: 15 * 60, 2: 35 * 60, 3: 60 * 60, 4: 85 * 60}
LEVELS = (1, 2, 3, 4)

# Algorithms: one problem per session, timed by difficulty.
ALGO_MINUTES = {"Easy": 20, "Medium": 30, "Hard": 40}
ALGO_DIFFICULTIES = tuple(ALGO_MINUTES)

# System design: one 45-minute slot, split by the seven framework steps in designs/framework.json.
DESIGN_TIME_LIMIT_SECONDS = 45 * 60

# Limits on a run. static/python.js applies the same ones in the browser.
RUN_TIMEOUT_SECONDS = 10
SCRATCH_TIMEOUT_SECONDS = 10
MAX_SCRATCH_OUTPUT = 50_000
