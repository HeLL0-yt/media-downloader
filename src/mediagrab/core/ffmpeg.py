"""Locate a complete FFmpeg installation and check both executable versions."""

import os
import re
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from mediagrab.core.errors import FfmpegNotFoundError, FfmpegVersionError
from mediagrab.core.process import run_process


@dataclass(frozen=True, slots=True)
class FfmpegPaths:
    """Paths to ffmpeg and ffprobe in one directory."""

    ffmpeg: Path
    ffprobe: Path

    @property
    def location(self) -> Path:
        """Return the directory to pass to yt-dlp's ffmpeg_location option."""
        return self.ffmpeg.parent


@dataclass(frozen=True, slots=True)
class FfmpegVersions:
    """Version tokens returned by a runnable FFmpeg and ffprobe pair."""

    ffmpeg: str
    ffprobe: str


def _search_directories() -> Iterator[Path]:
    executable = Path(sys.executable)
    if executable.is_absolute():
        yield executable.parent
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle and Path(bundle).is_absolute():
            yield Path(bundle)
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        directory = Path(entry)
        if entry and directory.is_absolute():
            yield directory


def locate_ffmpeg() -> FfmpegPaths | None:
    """Find executables next to the app, in its frozen bundle, then on PATH.

    Both binaries must be in one directory because yt-dlp's ffmpeg_location
    selects that directory for both. Empty or relative PATH entries are ignored
    to avoid selecting executables from an unrelated current directory.

    Returns:
        The first complete executable pair, or None if none is available.
    """
    suffix = ".exe" if os.name == "nt" else ""
    for directory in dict.fromkeys(_search_directories()):
        ffmpeg = directory / f"ffmpeg{suffix}"
        ffprobe = directory / f"ffprobe{suffix}"
        if all(path.is_file() and os.access(path, os.X_OK) for path in (ffmpeg, ffprobe)):
            return FfmpegPaths(ffmpeg=ffmpeg, ffprobe=ffprobe)
    return None


def _read_version(binary: Path, name: str) -> str:
    try:
        result = run_process([str(binary), "-version"], timeout=5.0)
    except (OSError, subprocess.SubprocessError) as error:
        raise FfmpegVersionError() from error
    match = re.search(rf"^{name} version (\S+)", result.stdout, flags=re.MULTILINE)
    if match is None:
        raise FfmpegVersionError(f"{name} did not return a valid version. Reinstall FFmpeg.")
    return match.group(1)


def get_ffmpeg_versions(paths: FfmpegPaths) -> FfmpegVersions:
    """Execute both version checks using bounded, shell-free processes.

    Release and Git snapshot version tokens are accepted. No arbitrary numeric
    minimum is imposed; media operations will report missing codec support.

    Args:
        paths: Discovered FFmpeg and ffprobe executable pair.

    Returns:
        Version tokens for the two executables.

    Raises:
        FfmpegVersionError: A binary fails, times out, or has an invalid banner.
    """
    return FfmpegVersions(
        ffmpeg=_read_version(paths.ffmpeg, "ffmpeg"),
        ffprobe=_read_version(paths.ffprobe, "ffprobe"),
    )


def ensure_ffmpeg() -> FfmpegPaths:
    """Require a discoverable and runnable FFmpeg/ffprobe installation.

    Returns:
        Validated paths to both executables.

    Raises:
        FfmpegNotFoundError: A complete installation cannot be found.
        FfmpegVersionError: A discovered binary cannot run correctly.
    """
    paths = locate_ffmpeg()
    if paths is None:
        raise FfmpegNotFoundError()
    get_ffmpeg_versions(paths)
    return paths
