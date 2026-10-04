"""Locate package data in installed source and PyInstaller onedir bundles."""

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    """Return an application resource without consulting the working directory."""
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("Resources must use a single filename.")
    if getattr(sys, "frozen", False):
        root = Path(sys._MEIPASS) / "mediagrab"  # type: ignore[attr-defined]
    else:
        root = Path(__file__).resolve().parent
    return root / "desktop" / "resources" / name
