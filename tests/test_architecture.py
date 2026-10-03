"""Enforce the dependency boundary between core and the desktop UI."""

import ast
from importlib.util import resolve_name
from pathlib import Path

import mediagrab.core


def test_core_has_no_gui_imports() -> None:
    assert mediagrab.core.__file__ is not None
    core_directory = Path(mediagrab.core.__file__).parent
    forbidden = ("PySide", "PyQt", "qtpy", "tkinter", "wx", "mediagrab.desktop")
    violations: list[str] = []

    for source in sorted(core_directory.rglob("*.py")):
        parts = source.relative_to(core_directory).with_suffix("").parts
        package = ".".join(("mediagrab", "core", *parts[:-1]))
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                name = "." * node.level + (node.module or "")
                base = resolve_name(name, package) if node.level else name
                names = [base, *(f"{base}.{alias.name}" for alias in node.names)]
            for name in names:
                if name.startswith(forbidden):
                    violations.append(f"{source.name}:{node.lineno}: {name}")

    assert not violations, "Core must not import GUI modules:\n" + "\n".join(violations)
