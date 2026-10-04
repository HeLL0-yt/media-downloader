"""Offline deployment checks, with machine-readable logging for windowed builds."""

import argparse
import importlib.metadata
import json
import logging
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from mediagrab import __version__
from mediagrab.core.environment import EnvironmentResult, Severity, inspect_environment
from mediagrab.core.process import run_process
from mediagrab.resources import resource_path

_LOGGER = logging.getLogger("mediagrab.self_check")
_REQUIRED = {"yt-dlp", "yt-dlp-ejs", "ffmpeg", "ffprobe", "deno", "Browser impersonation"}


def check_runtime() -> dict[str, object]:
    """Exercise dynamic engine imports, EJS data, native TLS and bundled discovery."""
    import certifi
    import yt_dlp_ejs.yt.solver
    from yt_dlp import YoutubeDL
    from yt_dlp.extractor import gen_extractor_classes

    # Initializing the engine loads postprocessors, networking handlers and plugins.
    with YoutubeDL({"quiet": True, "cachedir": False, "remote_components": []}) as engine:
        extractors = gen_extractor_classes()
        targets = engine._get_available_impersonate_targets()
    if not targets or len(extractors) < 1000:
        raise RuntimeError("Missing extractors or native impersonation targets.")
    scripts = [yt_dlp_ejs.yt.solver.core(), yt_dlp_ejs.yt.solver.lib()]
    if any(len(script) < 1000 for script in scripts):
        raise RuntimeError("EJS solver data is incomplete.")
    if "BEGIN CERTIFICATE" not in Path(certifi.where()).read_text(encoding="ascii"):
        raise RuntimeError("Certificate bundle is incomplete.")
    for name in ("dark.qss", "light.qss", "mediagrab.ico"):
        if not resource_path(name).is_file():
            raise RuntimeError(f"Missing application resource: {name}")
    report = inspect_environment()
    validate_environment(report)
    deno = next(item.location for item in report.items if item.name == "deno")
    # Parse and evaluate both real solver bundles in the selected Deno. No player
    # URL, remote module, npm cache or network permission is involved.
    with tempfile.TemporaryDirectory(prefix="mediagrab-ejs-") as directory:
        script = Path(directory) / "solver-check.js"
        script.write_text(
            scripts[1]
            + "\nObject.assign(globalThis, lib);\n"
            + scripts[0]
            + "\nconsole.log(JSON.stringify({solver: typeof jsc, parser: typeof meriyah}));",
            encoding="utf-8",
        )
        evaluation = run_process(
            [str(deno), "run", "--no-remote", "--no-npm", "--no-config", "--no-lock", str(script)],
            timeout=10,
        )
        if json.loads(evaluation.stdout) != {"solver": "function", "parser": "object"}:
            raise RuntimeError("Deno could not evaluate the packaged EJS solver.")
    return {
        "ok": True,
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "extractors": len(extractors),
        "ejs_script_lengths": [len(script) for script in scripts],
        "ejs_deno_evaluation": True,
        "certifi": certifi.where(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("mediagrab", "yt-dlp", "yt-dlp-ejs", "curl-cffi", "certifi", "PySide6")
        },
        "environment": [
            {
                "name": item.name,
                "severity": item.severity.value,
                "version": item.detail,
                "path": str(item.location) if item.location else None,
            }
            for item in report.items
        ],
    }


def validate_environment(report: EnvironmentResult) -> None:
    """Fail absent/broken required tools and external discovery in a frozen app."""
    items = {item.name: item for item in report.items}
    for name in sorted(_REQUIRED):
        if name not in items or items[name].severity is not Severity.OK:
            raise RuntimeError(f"Required capability failed: {name}")
    if getattr(sys, "frozen", False):
        directory = Path(sys.executable).resolve().parent
        for name in ("ffmpeg", "ffprobe", "deno"):
            location = items[name].location
            if location is None or location.resolve().parent != directory:
                raise RuntimeError(f"Tool was not discovered beside MediaGrab.exe: {name}")


def _output_stream() -> TextIO | None:
    """Recover redirected stdout when PyInstaller's windowed bootloader clears it."""
    if sys.stdout is not None:
        return sys.stdout
    if os.name != "nt":
        return None
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.DuplicateHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel.DuplicateHandle.restype = wintypes.BOOL
    handle = kernel.GetStdHandle(-11 & 0xFFFFFFFF)
    if not handle or handle == wintypes.HANDLE(-1).value:
        return None
    current = kernel.GetCurrentProcess()
    duplicate = wintypes.HANDLE()
    if not kernel.DuplicateHandle(current, handle, current, ctypes.byref(duplicate), 0, False, 2):
        return None
    descriptor = msvcrt.open_osfhandle(duplicate.value, os.O_WRONLY)
    return os.fdopen(descriptor, "w", encoding="utf-8", closefd=True)


def main(argv: Sequence[str]) -> int:
    """Run without a GUI, or exercise a temporary UI and orderly worker shutdown."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-check", action="store_true")
    modes.add_argument("--smoke-test", action="store_true")
    parser.add_argument(
        "--report", type=Path, help="JSON report path (recommended for windowed exe)"
    )
    arguments = parser.parse_args(argv)
    if getattr(sys, "frozen", False) and os.name == "nt":
        windows = Path(os.environ["SYSTEMROOT"])
        bundle = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        os.environ["PATH"] = os.pathsep.join(
            str(path) for path in (bundle / "PySide6", bundle, windows / "System32", windows)
        )
    stream = _output_stream()
    handlers: list[logging.Handler] = []
    if stream is not None:
        handlers.append(logging.StreamHandler(stream))
    if arguments.report is not None:
        handlers.append(logging.FileHandler(arguments.report, mode="w", encoding="utf-8"))
    if not handlers:
        handlers.append(logging.FileHandler("self-check.json", mode="w", encoding="utf-8"))
    previous = _LOGGER.level, _LOGGER.propagate
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False
    for handler in handlers:
        handler.setFormatter(logging.Formatter("%(message)s"))
        _LOGGER.addHandler(handler)
    try:
        result = check_runtime()
        if arguments.smoke_test:
            from mediagrab.desktop.frozen_smoke import check_ui

            result["gui"] = check_ui()
        _LOGGER.info("%s", json.dumps(result, ensure_ascii=True))
        return 0
    except Exception as error:
        _LOGGER.error("%s", json.dumps({"ok": False, "error": str(error)}))
        return 1
    finally:
        for handler in handlers:
            _LOGGER.removeHandler(handler)
            handler.close()
        _LOGGER.setLevel(previous[0])
        _LOGGER.propagate = previous[1]
        if stream is not None and stream is not sys.stdout:
            stream.close()
