"""Shell-free execution and isolation of Windows-specific process behavior."""

import subprocess
import sys
from threading import Event, Timer
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mediagrab.core import process
from mediagrab.core.errors import DownloadCancelledError


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


def test_cancellable_process_drains_both_pipes() -> None:
    result = process.run_process(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('o'*200000); sys.stderr.write('e'*200000)",
        ],
        timeout=10,
        cancel_event=Event(),
    )
    assert result.stdout == "o" * 200000
    assert result.stderr == "e" * 200000


def test_cancellable_process_checks_exit_status() -> None:
    with pytest.raises(subprocess.CalledProcessError) as caught:
        process.run_process([sys.executable, "-c", "raise SystemExit(7)"], cancel_event=Event())
    assert caught.value.returncode == 7


def test_cancellation_before_process_start_does_not_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    event = Event()
    event.set()
    launcher = Mock()
    monkeypatch.setattr(subprocess, "Popen", launcher)
    with pytest.raises(DownloadCancelledError):
        process.run_process([sys.executable], cancel_event=event)
    launcher.assert_not_called()


@pytest.mark.parametrize("cancel", [True, False])
def test_running_process_is_reaped_on_cancel_or_timeout(
    monkeypatch: pytest.MonkeyPatch,
    cancel: bool,
) -> None:
    children: list[subprocess.Popen[str]] = []
    native_popen = subprocess.Popen

    def launch(*args: object, **kwargs: object) -> subprocess.Popen[str]:
        child = native_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", launch)
    event = Event()
    timer = Timer(0.2, event.set)
    if cancel:
        timer.start()
    try:
        expected = DownloadCancelledError if cancel else subprocess.TimeoutExpired
        with pytest.raises(expected):
            process.run_process(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                timeout=5 if cancel else 0.2,
                cancel_event=event,
            )
        assert len(children) == 1 and children[0].poll() is not None
    finally:
        timer.cancel()
        if cancel:
            timer.join()


def test_process_is_killed_if_termination_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    event = Event()
    child = Mock()
    child.poll.return_value = None
    child.communicate.side_effect = [subprocess.TimeoutExpired([], 0.1), ("", "")]
    launcher = Mock()
    launcher.return_value.__enter__ = Mock(return_value=child)
    launcher.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(subprocess, "Popen", launcher)
    with pytest.raises(subprocess.TimeoutExpired):
        process.run_process([sys.executable], timeout=0, cancel_event=event)
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
