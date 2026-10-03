"""Shell-free process execution and isolated Windows console-window handling."""

import os
import subprocess
import time
from collections.abc import Sequence
from threading import Event

from mediagrab.core.errors import DownloadCancelledError


def run_process(
    args: Sequence[str], *, timeout: float = 10.0, cancel_event: Event | None = None
) -> subprocess.CompletedProcess[str]:
    """Run an argument list with captured output and a finite timeout.

    Callers supply a resolved executable and explicit arguments. URL input is
    never interpreted as a command. Windows-specific process flags live here.

    Args:
        args: Executable and separate arguments, without shell interpolation.
        timeout: Maximum process duration in seconds.
        cancel_event: Optional cancellation checked while the child runs.

    Returns:
        Successful process result with UTF-8 text output.

    Raises:
        OSError: The executable cannot be launched.
        subprocess.CalledProcessError: The process exits unsuccessfully.
        subprocess.TimeoutExpired: The process exceeds the timeout.
        DownloadCancelledError: Cancellation was requested.
    """
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    if cancel_event is not None:
        return _run_cancellable(args, timeout, cancel_event, creationflags)
    return subprocess.run(  # noqa: S603 -- Callers provide executable paths; no shell is used.
        list(args),
        shell=False,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=creationflags,
    )


def _run_cancellable(
    args: Sequence[str], timeout: float, cancel_event: Event, creationflags: int
) -> subprocess.CompletedProcess[str]:
    if cancel_event.is_set():
        raise DownloadCancelledError()
    # communicate() drains both pipes, avoiding deadlocks on verbose FFmpeg output.
    with subprocess.Popen(  # noqa: S603 -- Explicit arguments, never a shell.
        list(args),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    ) as child:
        deadline = time.monotonic() + timeout
        try:
            while True:
                if cancel_event.is_set():
                    raise DownloadCancelledError()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(list(args), timeout)
                try:
                    stdout, stderr = child.communicate(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.communicate(timeout=2.0)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.communicate()
        result = subprocess.CompletedProcess(list(args), child.returncode, stdout, stderr)
        result.check_returncode()
        return result
