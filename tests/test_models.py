"""Core settings validation and immutable worker payloads."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import cast

import pytest

from mediagrab.core.errors import InvalidRequestError, InvalidUrlError
from mediagrab.core.models import (
    AUDIO_BITRATES,
    VIDEO_HEIGHTS,
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    FormatChoice,
    ProgressEvent,
    VideoInfo,
)


@pytest.mark.parametrize("height", [None, *VIDEO_HEIGHTS])
@pytest.mark.parametrize("bitrate", [None, *AUDIO_BITRATES])
def test_supported_format_choices(height: int | None, bitrate: int | None) -> None:
    choice = FormatChoice(max_height=height, audio_bitrate=bitrate)
    assert choice.max_height == height
    assert choice.audio_bitrate == bitrate


@pytest.mark.parametrize("value", [0, -1, 999, "1080", True, 1080.0])
def test_invalid_heights(value: object) -> None:
    with pytest.raises(InvalidRequestError):
        FormatChoice(max_height=cast(int, value))


@pytest.mark.parametrize("value", [0, -1, 256, "320", True, 320.0])
def test_invalid_bitrates(value: object) -> None:
    with pytest.raises(InvalidRequestError):
        FormatChoice(audio_bitrate=cast(int, value))


def test_invalid_mode_is_rejected() -> None:
    with pytest.raises(InvalidRequestError):
        FormatChoice(mode=cast(DownloadMode, "audio"))


def test_request_defaults_and_sensitive_repr(tmp_path: Path) -> None:
    request = DownloadRequest("  https://example.com/watch?token=private-token  ", tmp_path)
    assert request.url == "https://example.com/watch?token=private-token"
    assert request.format.mode is DownloadMode.VIDEO
    assert request.playlists is False
    assert request.prefer_compatibility is True
    assert request.embed_thumbnail is True
    assert request.cookies_browser is None
    assert "private-token" not in repr(request)
    with pytest.raises(FrozenInstanceError):
        request.playlists = True  # type: ignore[misc]


def test_request_rejects_unsafe_url(tmp_path: Path) -> None:
    with pytest.raises(InvalidUrlError):
        DownloadRequest("file:///private", tmp_path)


@pytest.mark.parametrize("field", ["playlists", "prefer_compatibility", "embed_thumbnail"])
def test_request_rejects_non_boolean_flags(field: str, tmp_path: Path) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path)
    with pytest.raises(InvalidRequestError):
        replace(request, **{field: "false"})


def test_request_rejects_invalid_destination_type() -> None:
    with pytest.raises(InvalidRequestError):
        DownloadRequest("https://example.com/video", cast(Path, "output"))


def test_request_rejects_invalid_format_type(tmp_path: Path) -> None:
    with pytest.raises(InvalidRequestError):
        DownloadRequest("https://example.com/video", tmp_path, format=cast(FormatChoice, "mp4"))


def test_request_rejects_arbitrary_browser_commands(tmp_path: Path) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path)
    with pytest.raises(InvalidRequestError):
        replace(request, cookies_browser="chrome --profile-directory=other")


def test_video_info_normalizes_heights_and_hides_urls() -> None:
    info = VideoInfo(
        title="Example",
        webpage_url="https://example.com/watch?token=private-page-token",
        extractor="example",
        thumbnail_url="https://example.com/image?token=private-image-token",
        available_heights=(1080, 360, 720, 1080),
    )
    assert info.available_heights == (360, 720, 1080)
    assert "private-page-token" not in repr(info)
    assert "private-image-token" not in repr(info)


@pytest.mark.parametrize("value", [0, -1, True, "720"])
def test_video_info_rejects_invalid_heights(value: object) -> None:
    with pytest.raises(InvalidRequestError):
        VideoInfo(
            "Example", "https://example.com/video", "example", available_heights=(cast(int, value),)
        )


@pytest.mark.parametrize(
    ("status", "downloaded", "total", "expected"),
    [
        (DownloadStatus.QUEUED, 0, None, None),
        (DownloadStatus.DOWNLOADING, 10, None, None),
        (DownloadStatus.DOWNLOADING, 0, 0, None),
        (DownloadStatus.DOWNLOADING, 10, -1, None),
        (DownloadStatus.DOWNLOADING, 25, 100, 25.0),
        (DownloadStatus.DOWNLOADING, -10, 100, 0.0),
        (DownloadStatus.DOWNLOADING, 150, 100, 100.0),
        (DownloadStatus.FINISHED, 0, None, 100.0),
    ],
)
def test_progress_percent_is_bounded_and_unknown_size_is_distinct(
    status: DownloadStatus, downloaded: int, total: int | None, expected: float | None
) -> None:
    event = ProgressEvent(status, downloaded_bytes=downloaded, total_bytes=total)
    assert event.percent == expected


def test_progress_snapshot_is_immutable() -> None:
    event = ProgressEvent(DownloadStatus.DOWNLOADING)
    with pytest.raises(FrozenInstanceError):
        event.downloaded_bytes = 100  # type: ignore[misc]
