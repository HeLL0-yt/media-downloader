"""Shell-free process execution and isolated Windows console-window handling."""

import os
import subprocess
from collections.abc import Sequence


def run_process(args: Sequence[str], *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    """Run an argument list with captured output and a finite timeout.

    Callers supply a resolved executable and explicit arguments. URL input is
    never interpreted as a command. Windows-specific process flags live here.

    Args:
        args: Executable and separate arguments, without shell interpolation.
        timeout: Maximum process duration in seconds.

    Returns:
        Successful process result with UTF-8 text output.

    Raises:
        OSError: The executable cannot be launched.
        subprocess.CalledProcessError: The process exits unsuccessfully.
        subprocess.TimeoutExpired: The process exceeds the timeout.
    """
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
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
