"""Shell-free execution and isolation of Windows-specific process behavior."""

import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mediagrab.core import process


@pytest.mark.parametrize("platform", ["nt", "posix"])
def test_process_uses_argument_list_timeout_and_checked_exit(
    platform: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = subprocess.CompletedProcess([], 0, "version", "")
    runner = Mock(return_value=expected)
    monkeypatch.setattr(process, "os", SimpleNamespace(name=platform))
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(subprocess, "run", runner)
    arguments = ("resolved-executable", "-version")
    assert process.run_process(arguments, timeout=5.0) is expected
    runner.assert_called_once_with(
        list(arguments),
        shell=False,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5.0,
        creationflags=0x08000000 if platform == "nt" else 0,
    )


def test_process_failure_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    error = subprocess.CalledProcessError(1, ["executable"])
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=error))
    with pytest.raises(subprocess.CalledProcessError) as caught:
        process.run_process(["resolved-executable"])
    assert caught.value is error
