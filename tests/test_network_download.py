"""Opt-in real downloads of Blender's CC-BY-3.0 Big Buck Bunny trailer.

Attribution: (c) copyright 2008, Blender Foundation / www.bigbuckbunny.org.
License source: https://peach.blender.org/about/. Media stays in pytest's temp folder.
"""

from pathlib import Path
from threading import Event

import pytest

from mediagrab.core.downloader import download, get_info
from mediagrab.core.ffmpeg import ensure_ffmpeg
from mediagrab.core.models import (
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    FormatChoice,
    ProgressEvent,
)
from mediagrab.core.postprocessors import probe_media

_TRAILER = "https://download.blender.org/peach/trailer/trailer_iphone.m4v"


@pytest.mark.network
def test_creative_commons_video_and_mp3(tmp_path: Path) -> None:
    tools = ensure_ffmpeg()  # Explicitly enabled tests fail if dependencies are missing.
    cancellation = Event()
    info = get_info(_TRAILER)
    assert info.title
    for mode, extension, codec in [
        (DownloadMode.VIDEO, ".mp4", "aac"),
        (DownloadMode.AUDIO, ".mp3", "mp3"),
    ]:
        events: list[ProgressEvent] = []
        result = download(
            DownloadRequest(_TRAILER, tmp_path / mode.value, FormatChoice(mode=mode)),
            events.append,
            cancellation,
        )
        assert result.is_file() and result.stat().st_size > 0
        assert result.suffix == extension
        streams = probe_media(result, tools, cancellation)
        assert any(
            stream["codec_type"] == "audio" and stream["codec_name"] == codec for stream in streams
        )
        videos = [stream for stream in streams if stream["codec_type"] == "video"]
        if mode is DownloadMode.VIDEO:
            assert videos and videos[0]["codec_name"] == "h264"
            assert videos[0]["pix_fmt"] in {"yuv420p", "yuvj420p"}
        else:
            assert not videos
        statuses = [event.status for event in events]
        assert statuses[-1] is DownloadStatus.FINISHED
        assert DownloadStatus.DOWNLOADING in statuses
        assert DownloadStatus.PROCESSING in statuses
