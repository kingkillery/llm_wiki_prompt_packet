#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "support" / "scripts" / "llm_wiki_agent_updater.py"
runpy.run_path(str(SOURCE), run_name="__main__")
