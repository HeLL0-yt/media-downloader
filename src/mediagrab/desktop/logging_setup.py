"""Rotating redacted local diagnostics with no desktop console tracebacks."""

import logging
import os
from copy import copy
from logging.handlers import RotatingFileHandler
from pathlib import Path

from mediagrab.core.logging_utils import format_exception, redact_message


class RedactedFormatter(logging.Formatter):
    """Format a copy so raw messages and exception fields never reach disk."""

    def format(self, record: logging.LogRecord) -> str:
        """Redact diagnostics and preserve every traceback frame safely."""
        safe = copy(record)
        safe.msg = redact_message(record.getMessage())
        safe.args = ()
        safe.exc_text = None
        if safe.exc_info and safe.exc_info[1] is not None:
            safe.msg += "\n" + format_exception(safe.exc_info[1])
        safe.exc_info = None
        safe.stack_info = None
        return super().format(safe)


def logs_directory() -> Path:
    """Return the application log directory for platform folder actions."""
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    return base / "MediaGrab" / "logs"


def configure_logging(log_dir: Path | None = None) -> RotatingFileHandler:
    """Route application diagnostics exclusively to five bounded local log files."""
    if log_dir is None:
        log_dir = logs_directory()
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "mediagrab.log", maxBytes=2 * 1024 * 1024, backupCount=4, encoding="utf-8"
    )
    handler.setFormatter(RedactedFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger = logging.getLogger("mediagrab")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(handler)
    return handler
