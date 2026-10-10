"""Paths for writable Integrated data when running from a packaged desktop build."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "Integrated"
    path.mkdir(parents=True, exist_ok=True)
    return path
