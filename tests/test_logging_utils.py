"""Authentication and signed URLs cannot reach engine diagnostic logs."""

import logging

import pytest

from mediagrab.core.logging_utils import EngineLogger, log_exception, redact_message


@pytest.mark.parametrize(
    "message",
    [
        "Failed: https://example.com/path?token=secret",
        "Request 'HTTP://example.com/?signature=secret' failed",
        "Cookie: session=secret\nadditional sensitive data",
        "Authorization: secret",
        "Bearer secret",
    ],
)
def test_redacts_authentication_and_urls(message: str) -> None:
    result = redact_message(message)
    assert "secret" not in result
    assert "additional sensitive data" not in result


def test_engine_logger_redacts_all_levels(caplog: pytest.LogCaptureFixture) -> None:
    logger = EngineLogger(logging.getLogger("engine-test"))
    with caplog.at_level(logging.DEBUG):
        logger.debug("GET https://example.com/?secret=yes")
        logger.warning("Cookie: secret")
        logger.error("Authorization: secret")
    assert [record.levelno for record in caplog.records] == [10, 30, 40]
    assert "secret" not in caplog.text


def test_traceback_retains_frames_and_redacts_chained_messages(
    caplog: pytest.LogCaptureFixture,
) -> None:
    try:
        try:
            raise ValueError("https://example.com/?secret=yes")
        except ValueError as error:
            raise RuntimeError("Cookie: secret") from error
    except RuntimeError as error:
        log_exception(logging.getLogger("trace-test"), "Download failed", error)
    assert "Traceback" in caplog.text
    assert "ValueError" in caplog.text
    assert "test_traceback_retains_frames" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "secret" not in caplog.text
