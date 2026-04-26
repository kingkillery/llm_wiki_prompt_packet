#!/usr/bin/env python3
"""Wrapper entrypoint for the dashboard server.

The source of truth lives at support/scripts/dashboard_server.py.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_support_dashboard() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "support" / "scripts" / "dashboard_server.py"
    spec = importlib.util.spec_from_file_location("support_dashboard_server", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load support dashboard module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_MODULE = _load_support_dashboard()

DashboardHandler = _MODULE.DashboardHandler
HTTPServer = _MODULE.HTTPServer
run_server = _MODULE.run_server
main = _MODULE.main


if __name__ == "__main__":
    raise SystemExit(main())
