"""Source/frozen resources, deployment diagnostics and bundled tool precedence."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from mediagrab import resources, self_check
from mediagrab.core import environment
from mediagrab.core.environment import EnvironmentItem, EnvironmentResult, Severity
from mediagrab.desktop.engine_panel import EnginePanel


def test_source_resources_ignore_cwd_and_nonfrozen_meipass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert "QProgressBar" in resources.resource_path("dark.qss").read_text(encoding="utf-8")
    assert resources.resource_path("mediagrab.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"


def test_frozen_resources_use_meipass_not_executable_or_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "app" / "_internal"
    data = bundle / "mediagrab" / "desktop" / "resources" / "light.qss"
    data.parent.mkdir(parents=True)
    data.write_text("frozen fixture", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "MediaGrab.exe"))
    monkeypatch.chdir(tmp_path)
    assert resources.resource_path("light.qss") == data
    assert resources.resource_path("light.qss").read_text() == "frozen fixture"


@pytest.mark.parametrize("name", ["../dark.qss", "", "..", "resources/dark.qss"])
def test_resources_reject_traversal(name: str) -> None:
    with pytest.raises(ValueError):
        resources.resource_path(name)


@pytest.mark.parametrize("next_to_exe", [False, True])
def test_frozen_deno_discovery_ignores_python_scripts_and_prefers_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, next_to_exe: bool
) -> None:
    executable = tmp_path / "app"
    internal = executable / "_internal"
    scripts = tmp_path / "python_scripts"
    on_path = tmp_path / "path"
    suffix = ".exe" if os.name == "nt" else ""
    for directory in (executable, internal, scripts, on_path):
        directory.mkdir(parents=True, exist_ok=True)
        if directory != executable or next_to_exe:
            tool = directory / f"deno{suffix}"
            tool.write_bytes(b"placeholder, never executed")
            tool.chmod(0o755)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(internal), raising=False)
    monkeypatch.setattr(sys, "executable", str(executable / "MediaGrab.exe"))
    monkeypatch.setattr(environment.sysconfig, "get_path", lambda _name: str(scripts))
    monkeypatch.setenv("PATH", str(on_path))
    expected = executable if next_to_exe else internal
    assert environment.runtime_options()["deno"]["path"] == str(expected / f"deno{suffix}")


def report(directory: Path) -> EnvironmentResult:
    return EnvironmentResult(
        tuple(
            EnvironmentItem(
                name,
                Severity.OK,
                "fixture",
                location=directory / f"{name}.exe"
                if name in {"ffmpeg", "ffprobe", "deno"}
                else None,
            )
            for name in self_check._REQUIRED
        )
    )


def test_self_check_rejects_external_tools_and_absent_capabilities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "MediaGrab.exe"))
    self_check.validate_environment(report(tmp_path / "app"))
    with pytest.raises(RuntimeError, match="beside MediaGrab"):
        self_check.validate_environment(report(tmp_path / "system"))
    with pytest.raises(RuntimeError, match="Required capability"):
        self_check.validate_environment(EnvironmentResult(()))


def test_runtime_check_exercises_installed_extractors_ejs_native_targets_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(self_check, "inspect_environment", lambda: report(tmp_path))
    monkeypatch.setattr(
        self_check,
        "run_process",
        Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, '{"solver":"function","parser":"object"}', ""
            )
        ),
    )
    result = self_check.check_runtime()
    assert result["ok"]
    assert result["extractors"] > 1000
    assert all(size > 1000 for size in result["ejs_script_lengths"])
    assert "yt-dlp-ejs" in result["packages"]


@pytest.mark.parametrize("failure", [False, True])
def test_self_check_logs_json_report_and_exit_code_without_a_gui(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: bool
) -> None:
    operation = Mock(return_value={"ok": True, "version": "fixture"})
    if failure:
        operation.side_effect = RuntimeError("missing tool")
    monkeypatch.setattr(self_check, "check_runtime", operation)
    monkeypatch.setattr(self_check, "_output_stream", lambda: None)
    output = tmp_path / "report.json"
    assert self_check.main(["--self-check", "--report", str(output)]) == int(failure)
    result = json.loads(output.read_text())
    assert result["ok"] == (not failure)
    if failure:
        assert result["error"] == "missing tool"


def test_frozen_panel_explains_updating_app_and_refuses_pip(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    parent = QWidget()
    qtbot.addWidget(parent)
    panel = EnginePanel(parent, Mock(), Mock(return_value=False), Mock())
    assert "Update MediaGrab to get a newer engine" in panel.status.text()
    operation = Mock()
    monkeypatch.setattr(panel, "start", operation)
    panel.confirm_update()
    operation.assert_not_called()
    assert not panel.update.isEnabled()
