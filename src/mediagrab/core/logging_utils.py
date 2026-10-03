"""Redacted engine diagnostics without cookies or signed URLs."""

import logging
import re
import traceback

_URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_SECRET = re.compile(r"cookie|authorization|bearer\s", re.IGNORECASE)


def redact_message(message: str) -> str:
    """Remove URLs and suppress diagnostics containing authentication data.

    Args:
        message: Untrusted engine diagnostic text.

    Returns:
        Text suitable for a log file.
    """
    if _SECRET.search(message):
        return "[authentication diagnostic redacted]"
    return _URL.sub("[URL redacted]", message)


def log_exception(logger: logging.Logger, message: str, error: BaseException) -> None:
    """Log traceback frames and redacted exception details without locals.

    Args:
        logger: Destination logger.
        message: Application-owned description of the failed operation.
        error: Exception with its original traceback and cause.
    """
    trace = traceback.TracebackException.from_exception(error, capture_locals=False)
    details = _format_trace(trace)
    logger.error("%s\n%s", redact_message(message), details)


def _format_trace(trace: traceback.TracebackException) -> str:
    parts: list[str] = []
    if trace.__cause__ is not None:
        parts += [_format_trace(trace.__cause__), "\nThe above exception caused this failure:\n"]
    elif trace.__context__ is not None and not trace.__suppress_context__:
        parts += [_format_trace(trace.__context__), "\nDuring handling of the above exception:\n"]
    parts.append("Traceback (most recent call last):\n")
    # Retain every frame without logging source lines, locals, or frame reprs.
    for frame in trace.stack:
        filename = _URL.sub("[URL redacted]", frame.filename)
        parts.append(f'  File "{filename}", line {frame.lineno}, in {frame.name}\n')
    diagnostic = redact_message("".join(trace.format_exception_only()))
    if diagnostic == "[authentication diagnostic redacted]":
        diagnostic = f"{trace.exc_type_str}: {diagnostic}\n"
    parts.append(diagnostic)
    return "".join(parts)


class EngineLogger:
    """Adapt yt-dlp's logger protocol while redacting every diagnostic."""

    def __init__(self, logger: logging.Logger) -> None:
        """Keep the application logger used for engine output."""
        self._logger = logger

    def debug(self, message: str) -> None:
        """Record engine diagnostics without sensitive input."""
        self._logger.debug("%s", redact_message(message))

    def warning(self, message: str) -> None:
        """Record a redacted engine warning."""
        self._logger.warning("%s", redact_message(message))

    def error(self, message: str) -> None:
        """Record a redacted engine error."""
        self._logger.error("%s", redact_message(message))
