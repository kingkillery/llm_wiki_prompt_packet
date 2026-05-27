#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[3] / "installers" / "wire_repo_agent_hooks.py"
runpy.run_path(str(INSTALLER), run_name="__main__")
