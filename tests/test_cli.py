"""Manual CLI settings, success, failures, and interrupt behavior."""

import logging
import sys
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest

from mediagrab.core import cli
from mediagrab.core.env_check import EnvironmentReport
from mediagrab.core.errors import DownloadCancelledError, NetworkError
from mediagrab.core.logging_utils import log_exception
from mediagrab.core.models import (
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    ProgressCallback,
    ProgressEvent,
)


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli,
        "check_environment",
        lambda: EnvironmentReport("test-version", ("chrome:windows",)),
    )


def test_cli_audio_and_height_example(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock()
    monkeypatch.setattr(cli, "download", runner)
    assert (
        cli.main(
            [
                "https://example.com/video",
                "--audio",
                "--height",
                "1080",
                "--bitrate",
                "192",
                "--output-dir",
                str(tmp_path),
                "--playlists",
                "--cookies-from-browser",
                "edge",
                "--no-thumbnail",
                "--no-compatibility",
            ]
        )
        == 0
    )
    request, callback, event = runner.call_args.args
    assert request.format.mode is DownloadMode.AUDIO
    assert request.format.max_height == 1080 and request.format.audio_bitrate == 192
    assert request.output_dir == tmp_path
    assert request.playlists and request.cookies_browser == "edge"
    assert not request.embed_thumbnail and not request.prefer_compatibility
    assert callable(callback) and not event.is_set()


def test_cli_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock()
    monkeypatch.setattr(cli, "download", runner)
    assert cli.main(["https://example.com/video"]) == 0
    request = runner.call_args.args[0]
    assert request.format.mode is DownloadMode.VIDEO
    assert request.format.max_height is None and request.format.audio_bitrate is None
    assert request.output_dir == Path("downloads")
    assert not request.playlists


@pytest.mark.parametrize("error", [NetworkError(), DownloadCancelledError(), KeyboardInterrupt()])
def test_cli_failure_exit_codes(error: BaseException, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "download", Mock(side_effect=error))
    expected = 1 if isinstance(error, NetworkError) else 130
    assert cli.main(["https://example.com/video"]) == expected


def test_invalid_url_is_a_safe_cli_error(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock()
    monkeypatch.setattr(cli, "download", runner)
    assert cli.main(["file:///video"]) == 1
    runner.assert_not_called()


@pytest.mark.parametrize("option", [["--height", "1000"], ["--bitrate", "256"]])
def test_cli_rejects_unsupported_settings(option: list[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["https://example.com/video", *option])
    assert caught.value.code == 2


@pytest.mark.parametrize("status", list(DownloadStatus))
def test_cli_logs_progress(status: DownloadStatus, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        cli._progress(
            ProgressEvent(status, downloaded_bytes=1, total_bytes=2, message="Safe message")
        )
    if status in {DownloadStatus.ERROR, DownloadStatus.CANCELLED}:
        assert not caplog.records
    else:
        assert caplog.records


def test_unknown_progress_does_not_log_a_fake_percentage(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        cli._progress(ProgressEvent(DownloadStatus.DOWNLOADING))
    assert not caplog.records


@pytest.mark.parametrize("verbose", [False, True])
def test_cli_tracebacks_are_opt_in_and_always_redacted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    verbose: bool,
) -> None:
    def fail(*args: object) -> None:
        try:
            raise ValueError("https://example.com/?token=secret")
        except ValueError as error:
            log_exception(logging.getLogger("mediagrab.core.downloader"), "Download failed.", error)
            raise NetworkError() from error

    monkeypatch.setattr(cli, "download", fail)
    arguments = ["https://example.com/video", *(["--verbose"] if verbose else [])]
    assert cli.main(arguments) == 1
    console = capsys.readouterr().err
    assert "Check your connection" in console
    assert ("Traceback" in console) is verbose
    assert ("ValueError" in console) is verbose
    assert "secret" not in console
    assert "https://example.com" not in console


def test_cli_reports_environment_warning_and_still_downloads(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "check_environment",
        lambda: EnvironmentReport("test-version", (), ("Install curl-cffi.",)),
    )
    download = Mock()
    monkeypatch.setattr(cli, "download", download)
    assert cli.main(["https://example.com/video"]) == 0
    download.assert_called_once()
    assert "WARNING: Install curl-cffi." in capsys.readouterr().err


def test_cli_logging_restores_existing_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = logging.getLogger("mediagrab")
    previous = logger.level, logger.propagate, list(logger.handlers)
    monkeypatch.setattr(cli, "download", Mock(side_effect=NetworkError()))
    for arguments in (["https://example.com"], ["https://example.com", "--verbose"]):
        assert cli.main(arguments) == 1
        assert (logger.level, logger.propagate, logger.handlers) == previous


@pytest.mark.parametrize("verbose", [False, True])
def test_console_formatter_hides_raw_exception_fields_and_preserves_record(verbose: bool) -> None:
    try:
        raise RuntimeError("https://example.com/?secret=yes")
    except RuntimeError:
        record = logging.LogRecord(
            "mediagrab", logging.ERROR, __file__, 1, "Safe message", (), sys.exc_info()
        )
    original = record.exc_info
    record.exc_text = "Cached Python traceback"
    record.stack_info = "Raw stack source code"
    text = cli._ConsoleFormatter(verbose).format(record)
    assert ("Traceback" in text) is verbose
    assert "Raw stack source code" not in text
    assert "secret" not in text
    assert record.exc_info is original
    assert record.exc_text == "Cached Python traceback"


def test_cli_prints_terminal_error_only_once(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(request: DownloadRequest, on_progress: ProgressCallback, event: Event) -> None:
        on_progress(ProgressEvent(DownloadStatus.ERROR, message=str(NetworkError())))
        raise NetworkError()

    monkeypatch.setattr(cli, "download", fail)
    assert cli.main(["https://example.com"]) == 1
    assert capsys.readouterr().err.count(str(NetworkError())) == 1


def test_console_never_reuses_untrusted_cached_traceback_text() -> None:
    record = logging.LogRecord("mediagrab", logging.ERROR, __file__, 1, "Safe message", (), None)
    record.exc_text = "Traceback source line with a private value"
    record.stack_info = "Raw source stack"
    for verbose in (False, True):
        assert cli._ConsoleFormatter(verbose).format(record) == "ERROR: Safe message"
    assert record.exc_text == "Traceback source line with a private value"
