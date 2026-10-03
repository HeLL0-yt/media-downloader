"""FFmpeg search precedence and safe, bounded version checks."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from mediagrab.core import ffmpeg
from mediagrab.core.errors import FfmpegNotFoundError, FfmpegVersionError
from mediagrab.core.ffmpeg import FfmpegPaths, FfmpegVersions


@pytest.fixture(autouse=True)
def isolated_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python" / "python.exe"))
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setenv("PATH", "")


def _make_pair(directory: Path) -> FfmpegPaths:
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    binaries = FfmpegPaths(directory / f"ffmpeg{suffix}", directory / f"ffprobe{suffix}")
    for binary in (binaries.ffmpeg, binaries.ffprobe):
        binary.write_bytes(b"test placeholder, never executed")
        binary.chmod(0o755)
    return binaries


def test_executable_directory_wins_over_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundled = _make_pair(Path(sys.executable).parent)
    on_path = _make_pair(tmp_path / "path")
    monkeypatch.setenv("PATH", str(on_path.location))
    assert ffmpeg.locate_ffmpeg() == bundled


def test_frozen_executable_directory_wins_over_meipass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundled = _make_pair(tmp_path / "application")
    internal = _make_pair(tmp_path / "internal")
    monkeypatch.setattr(sys, "executable", str(bundled.location / "MediaGrab.exe"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(internal.location), raising=False)
    assert ffmpeg.locate_ffmpeg() == bundled


def test_meipass_wins_over_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    internal = _make_pair(tmp_path / "internal")
    on_path = _make_pair(tmp_path / "path")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(internal.location), raising=False)
    monkeypatch.setenv("PATH", str(on_path.location))
    assert ffmpeg.locate_ffmpeg() == internal


def test_meipass_is_ignored_when_not_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    internal = _make_pair(tmp_path / "internal")
    on_path = _make_pair(tmp_path / "path")
    monkeypatch.setattr(sys, "_MEIPASS", str(internal.location), raising=False)
    monkeypatch.setenv("PATH", str(on_path.location))
    assert ffmpeg.locate_ffmpeg() == on_path


def test_frozen_without_meipass_falls_back_to_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on_path = _make_pair(tmp_path / "path")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("PATH", str(on_path.location))
    assert ffmpeg.locate_ffmpeg() == on_path


def test_incomplete_bundled_pair_falls_back_to_complete_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundled = _make_pair(Path(sys.executable).parent)
    bundled.ffprobe.unlink()
    on_path = _make_pair(tmp_path / "path")
    monkeypatch.setenv("PATH", str(on_path.location))
    assert ffmpeg.locate_ffmpeg() == on_path


def test_split_installation_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = _make_pair(tmp_path / "first")
    second = _make_pair(tmp_path / "second")
    first.ffprobe.unlink()
    second.ffmpeg.unlink()
    monkeypatch.setenv("PATH", os.pathsep.join([str(first.location), str(second.location)]))
    assert ffmpeg.locate_ffmpeg() is None


def test_empty_and_relative_path_entries_do_not_search_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = _make_pair(tmp_path / "cwd")
    monkeypatch.chdir(current.location)
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", "relative"]))
    assert ffmpeg.locate_ffmpeg() is None


def test_non_executable_binary_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_pair(Path(sys.executable).parent)
    monkeypatch.setattr(ffmpeg.os, "access", Mock(return_value=False))
    assert ffmpeg.locate_ffmpeg() is None


def test_missing_pair_has_installation_instructions() -> None:
    with pytest.raises(FfmpegNotFoundError, match="PATH") as caught:
        ffmpeg.ensure_ffmpeg()
    assert "ffprobe" in str(caught.value)
    assert "next to MediaGrab" in str(caught.value)


def test_release_and_snapshot_version_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = _make_pair(tmp_path / "tools")
    runner = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0, "ffmpeg version 8.0 Copyright\n", ""),
            subprocess.CompletedProcess([], 0, "ffprobe version N-123-gabcdef Copyright\n", ""),
        ]
    )
    monkeypatch.setattr(ffmpeg, "run_process", runner)
    assert ffmpeg.get_ffmpeg_versions(pair) == FfmpegVersions("8.0", "N-123-gabcdef")
    assert runner.call_args_list[0].args == ([str(pair.ffmpeg), "-version"],)
    assert runner.call_args_list[1].args == ([str(pair.ffprobe), "-version"],)
    assert all(call.kwargs == {"timeout": 5.0} for call in runner.call_args_list)


@pytest.mark.parametrize(
    "error",
    [
        PermissionError("Executable is blocked"),
        subprocess.TimeoutExpired(["ffmpeg", "-version"], 5),
        subprocess.CalledProcessError(1, ["ffmpeg", "-version"]),
    ],
)
def test_failed_version_checks_are_typed(
    error: Exception, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = _make_pair(tmp_path / "tools")
    monkeypatch.setattr(ffmpeg, "run_process", Mock(side_effect=error))
    with pytest.raises(FfmpegVersionError) as caught:
        ffmpeg.get_ffmpeg_versions(pair)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("banner", ["", "not ffmpeg", "ffprobe version 8.0\n"])
def test_invalid_version_banner_is_rejected(
    banner: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = _make_pair(tmp_path / "tools")
    monkeypatch.setattr(
        ffmpeg, "run_process", Mock(return_value=subprocess.CompletedProcess([], 0, banner, ""))
    )
    with pytest.raises(FfmpegVersionError, match="valid version"):
        ffmpeg.get_ffmpeg_versions(pair)


def test_ensure_checks_versions_and_returns_the_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pair = _make_pair(tmp_path / "tools")
    monkeypatch.setenv("PATH", str(pair.location))
    version_check = Mock(return_value=FfmpegVersions("8.0", "8.0"))
    monkeypatch.setattr(ffmpeg, "get_ffmpeg_versions", version_check)
    assert ffmpeg.ensure_ffmpeg() == pair
    version_check.assert_called_once_with(pair)
