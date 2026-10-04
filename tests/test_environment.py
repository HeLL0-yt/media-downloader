"""Offline environment coverage using mocked packages, tools and version banners."""

import os
import subprocess
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest
from yt_dlp.globals import supported_js_runtimes

from mediagrab.core import environment, ffmpeg
from mediagrab.core.env_check import EnvironmentReport
from mediagrab.core.errors import DownloadCancelledError, FfmpegVersionError
from mediagrab.core.ffmpeg import FfmpegPaths, FfmpegVersions


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(environment, "check_environment", lambda: EnvironmentReport("test", (), ()))
    monkeypatch.setattr(environment, "locate_ffmpeg", lambda: None)
    monkeypatch.setattr(environment, "locate_media_binary", lambda _name: None)
    monkeypatch.setattr(environment, "runtime_options", lambda: {})
    monkeypatch.setattr(environment.importlib.metadata, "version", lambda _name: "test-ejs")


def test_missing_environment_items_have_hints(
    offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(_name: str) -> str:
        raise environment.importlib.metadata.PackageNotFoundError()

    monkeypatch.setattr(environment.importlib.metadata, "version", missing)
    result = environment.inspect_environment()
    items = {item.name: item for item in result.items}
    assert items["ffmpeg"].severity is environment.Severity.ERROR
    assert items["ffprobe"].severity is environment.Severity.ERROR
    assert items["YouTube JavaScript"].severity is environment.Severity.WARNING
    assert "DenoLand.Deno" in items["YouTube JavaScript"].fix_hint
    assert "pip install" in items["yt-dlp-ejs"].fix_hint
    assert "curl-cffi" in items["Browser impersonation"].fix_hint
    assert all(item.fix_hint for item in result.items if item.severity != environment.Severity.OK)


@pytest.mark.parametrize("broken", [False, True])
def test_media_versions_and_locations(
    offline: None,
    monkeypatch: pytest.MonkeyPatch,
    broken: bool,
) -> None:
    paths = FfmpegPaths(Path("ffmpeg.exe"), Path("ffprobe.exe"))
    monkeypatch.setattr(environment, "locate_ffmpeg", lambda: paths)

    def versions(_paths: FfmpegPaths) -> FfmpegVersions:
        if broken:
            raise FfmpegVersionError()
        return FfmpegVersions("8", "8-probe")

    monkeypatch.setattr(environment, "get_ffmpeg_versions", versions)
    items = {item.name: item for item in environment.inspect_environment().items}
    assert items["ffmpeg"].location == paths.ffmpeg
    assert items["ffprobe"].location == paths.ffprobe
    assert items["ffmpeg"].severity == (
        environment.Severity.ERROR if broken else environment.Severity.OK
    )


@pytest.mark.parametrize(
    "name,banner,ok",
    [
        ("deno", "deno 2.3.0", True),
        ("deno", "deno 2.2.0", False),
        ("node", "v22.0.0", True),
        ("node", "v20.1.0", False),
        ("bun", "1.2.11", True),
        ("quickjs", "QuickJS version 2023-12-09", True),
        ("quickjs", "QuickJS-ng version 0.10.0", True),
        ("deno", "unexpected", False),
    ],
)
def test_runtime_banners_use_installed_engine_minimums(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    banner: str,
    ok: bool,
) -> None:
    runner = Mock(return_value=subprocess.CompletedProcess([], 0, banner, ""))
    monkeypatch.setattr(environment, "run_process", runner)
    item = environment._runtime_item(name, Path("tool.exe"), Event())
    assert (item.severity == environment.Severity.OK) == ok
    assert runner.call_args.kwargs["timeout"] == 5
    assert item.location == Path("tool.exe")


@pytest.mark.parametrize(
    "failure",
    [
        OSError(),
        subprocess.TimeoutExpired([], 5),
        subprocess.CalledProcessError(1, [], "QuickJS version 2024-01-01"),
    ],
)
def test_runtime_failures_are_warnings_or_quickjs_success(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    monkeypatch.setattr(environment, "run_process", Mock(side_effect=failure))
    name = "quickjs" if isinstance(failure, subprocess.CalledProcessError) else "deno"
    result = environment._runtime_item(name, Path("runtime"), Event())
    assert result.severity == (
        environment.Severity.OK if name == "quickjs" else environment.Severity.WARNING
    )


def test_discovery_ignores_cwd_and_enables_installed_alternatives(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    path_dir = tmp_path / "path"
    path_dir.mkdir()
    suffix = ".exe" if os.name == "nt" else ""
    for directory, name in ((scripts, "node"), (path_dir, "qjs")):
        (directory / (name + suffix)).touch()
    monkeypatch.setattr(environment.sysconfig, "get_path", lambda _name: str(scripts))
    monkeypatch.setattr(environment.os, "access", lambda *_args: True)
    monkeypatch.setenv("PATH", os.pathsep.join((".", "", str(path_dir))))
    result = environment.runtime_options()
    assert result == {
        "node": {"path": str(scripts / ("node" + suffix))},
        "quickjs": {"path": str(path_dir / ("qjs" + suffix))},
    }
    assert set(result) <= supported_js_runtimes.value.keys()


def test_supported_runtime_summary_and_cancellation(
    offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(environment, "runtime_options", lambda: {"node": {"path": "node.exe"}})
    monkeypatch.setattr(
        environment,
        "run_process",
        Mock(return_value=subprocess.CompletedProcess([], 0, "v22.0.0", "")),
    )
    items = {item.name: item for item in environment.inspect_environment().items}
    assert items["YouTube JavaScript"].severity == environment.Severity.OK
    cancel = Event()
    cancel.set()
    with pytest.raises(DownloadCancelledError):
        environment.inspect_environment(cancel)


def test_single_media_binary_diagnostic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ffmpeg, "_search_directories", lambda: iter([tmp_path]))
    assert ffmpeg.locate_media_binary("ffmpeg") is None
    binary = tmp_path / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    binary.touch()
    monkeypatch.setattr(ffmpeg.os, "access", lambda *_args: True)
    assert ffmpeg.locate_media_binary("ffmpeg") == binary


@pytest.mark.parametrize("broken", [False, True])
def test_incomplete_pair_reports_found_binary_version(
    offline: None,
    monkeypatch: pytest.MonkeyPatch,
    broken: bool,
) -> None:
    monkeypatch.setattr(
        environment,
        "locate_media_binary",
        lambda name: Path("ffmpeg.exe") if name == "ffmpeg" else None,
    )

    def version(_binary: Path, _name: str) -> str:
        if broken:
            raise FfmpegVersionError()
        return "8"

    monkeypatch.setattr(environment, "get_media_binary_version", version)
    items = {item.name: item for item in environment.inspect_environment().items}
    assert items["ffmpeg"].location == Path("ffmpeg.exe")
    assert "pair incomplete" in items["ffmpeg"].detail
    assert items["ffprobe"].detail == "Not found"


def test_public_single_binary_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ffmpeg,
        "run_process",
        Mock(return_value=subprocess.CompletedProcess([], 0, "ffmpeg version 8", "")),
    )
    assert ffmpeg.get_media_binary_version(Path("ffmpeg.exe"), "ffmpeg") == "8"
