"""Bounded offline engine, media-tool and JavaScript environment diagnostics."""

import importlib.metadata
import os
import re
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Event

from yt_dlp.globals import supported_js_runtimes

from mediagrab.core.env_check import check_environment
from mediagrab.core.errors import DownloadCancelledError, MediaGrabError
from mediagrab.core.ffmpeg import (
    get_ffmpeg_versions,
    get_media_binary_version,
    locate_ffmpeg,
    locate_media_binary,
)
from mediagrab.core.process import run_process


class Severity(StrEnum):
    """User-facing importance of one diagnostic item."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class EnvironmentItem:
    """One offline capability, including a local executable location if found."""

    name: str
    severity: Severity
    detail: str
    fix_hint: str = ""
    location: Path | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentResult:
    """Immutable full diagnostic snapshot; warnings never disable downloads."""

    items: tuple[EnvironmentItem, ...]


def runtime_options() -> dict[str, dict[str, str]]:
    """Configure installed-engine runtimes using explicit trusted search locations.

    Verified against yt-dlp 2026.08.19 YoutubeDL.js_runtimes and utils/_jsruntime.py.
    Search Python's scripts folder and absolute PATH directories, excluding cwd.
    Runtime support/version rules remain owned by the installed engine.
    """
    directories = (
        [Path(sys.executable).parent, Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))]
        if getattr(sys, "frozen", False)
        else [Path(sysconfig.get_path("scripts"))]
    )
    directories.extend(
        Path(entry)
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and Path(entry).is_absolute()
    )
    options: dict[str, dict[str, str]] = {}
    for name in supported_js_runtimes.value:
        basename = "qjs" if name == "quickjs" else name
        for directory in dict.fromkeys(directories):
            binary = directory / (basename + (".exe" if os.name == "nt" else ""))
            if binary.is_file() and os.access(binary, os.X_OK):
                options[name] = {"path": str(binary.absolute())}
                break
    return options


def _runtime_item(name: str, path: Path, cancel: Event) -> EnvironmentItem:
    hint = "Install/update Deno: winget install DenoLand.Deno; restart MediaGrab."
    try:
        args = [str(path), "--help" if name == "quickjs" else "--version"]
        try:
            result = run_process(args, timeout=5, cancel_event=cancel)
            output = result.stdout + result.stderr
        except subprocess.CalledProcessError as error:
            if name != "quickjs" or error.returncode != 1:
                raise
            output = (error.stdout or "") + (error.stderr or "")
        patterns = {
            "deno": r"^deno (\S+)",
            "node": r"^v(\S+)",
            "bun": r"^(\S+)",
            "quickjs": r"^QuickJS(?:-ng)?\s+version\s+(\S+)",
        }
        match = re.search(patterns[name], output, re.MULTILINE)
        version = match.group(1) if match else "unknown"
        # Upstream version_tuple lenient behavior for the documented banners.
        from yt_dlp.utils import version_tuple

        value = version_tuple(version, lenient=True)
        minimum = supported_js_runtimes.value[name].MIN_SUPPORTED_VERSION
        supported = (
            value > (0,) if name == "quickjs" and "QuickJS-ng" in output else value >= minimum
        )
        return EnvironmentItem(
            name,
            Severity.OK if supported else Severity.WARNING,
            f"{version}" + (" (unsupported version)" if not supported else ""),
            "" if supported else hint,
            path,
        )
    except OSError, subprocess.SubprocessError:
        return EnvironmentItem(
            name, Severity.WARNING, "Version probe failed or timed out", hint, path
        )


def inspect_environment(cancel_event: Event | None = None) -> EnvironmentResult:
    """Inspect installed packages and executables offline with bounded probes."""
    cancel = cancel_event if cancel_event is not None else Event()
    report = check_environment()
    items = [EnvironmentItem("yt-dlp", Severity.OK, report.yt_dlp_version)]
    try:
        ejs = importlib.metadata.version("yt-dlp-ejs")
        items.append(EnvironmentItem("yt-dlp-ejs", Severity.OK, ejs))
    except importlib.metadata.PackageNotFoundError:
        items.append(
            EnvironmentItem(
                "yt-dlp-ejs",
                Severity.WARNING,
                "Not installed",
                'Use the app Python: python -m pip install "yt-dlp[default,curl-cffi]"; restart.',
            )
        )
    paths = locate_ffmpeg()
    if paths is None:
        for name in ("ffmpeg", "ffprobe"):
            binary = locate_media_binary(name)
            detail = "Not found"
            if binary is not None:
                try:
                    detail = (
                        get_media_binary_version(binary, name) + " (executable pair incomplete)"
                    )
                except MediaGrabError:
                    detail = "Found but version probe failed (executable pair incomplete)"
            items.append(
                EnvironmentItem(
                    name,
                    Severity.ERROR,
                    detail,
                    "Install both executables together: winget install Gyan.FFmpeg; "
                    "restart MediaGrab.",
                    binary,
                )
            )
    else:
        try:
            versions = get_ffmpeg_versions(paths)
            for name in ("ffmpeg", "ffprobe"):
                items.append(
                    EnvironmentItem(
                        name, Severity.OK, getattr(versions, name), location=getattr(paths, name)
                    )
                )
        except MediaGrabError:
            for name in ("ffmpeg", "ffprobe"):
                items.append(
                    EnvironmentItem(
                        name,
                        Severity.ERROR,
                        "Version check failed",
                        "Reinstall FFmpeg and restart MediaGrab.",
                        getattr(paths, name),
                    )
                )
    runtimes = runtime_options()
    for name in supported_js_runtimes.value:
        if cancel.is_set():
            raise DownloadCancelledError()
        if name in runtimes:
            items.append(_runtime_item(name, Path(runtimes[name]["path"]), cancel))
        else:
            items.append(
                EnvironmentItem(
                    name,
                    Severity.WARNING,
                    "Not found (optional alternative)",
                    "Install Deno (recommended): winget install DenoLand.Deno.",
                )
            )
    usable = any(item.name in runtimes and item.severity is Severity.OK for item in items)
    items.append(
        EnvironmentItem(
            "YouTube JavaScript",
            Severity.OK if usable else Severity.WARNING,
            "Supported runtime available" if usable else "No supported external runtime",
            "" if usable else "winget install DenoLand.Deno; restart MediaGrab.",
        )
    )
    items.append(
        EnvironmentItem(
            "Browser impersonation",
            Severity.OK if report.impersonation_targets else Severity.WARNING,
            ", ".join(report.impersonation_targets) or "No targets available",
            ""
            if report.impersonation_targets
            else 'Use the app Python: python -m pip install "yt-dlp[default,curl-cffi]"; restart.',
        )
    )
    return EnvironmentResult(tuple(items))
