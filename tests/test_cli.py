"""Manual CLI settings, success, failures, and interrupt behavior."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from mediagrab.core import cli
from mediagrab.core.errors import DownloadCancelledError, NetworkError
from mediagrab.core.models import DownloadMode, DownloadStatus, ProgressEvent


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
    assert caplog.records


def test_unknown_progress_does_not_log_a_fake_percentage(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        cli._progress(ProgressEvent(DownloadStatus.DOWNLOADING))
    assert not caplog.records
