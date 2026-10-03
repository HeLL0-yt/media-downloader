"""Mocked engine operations, metadata, progress, paths, and cancellation."""

from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Event
from typing import Any
from unittest.mock import Mock

import pytest
import yt_dlp
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import DownloadError

from mediagrab.core import downloader
from mediagrab.core.errors import (
    DownloadCancelledError,
    ExtractionError,
    FfmpegNotFoundError,
    InvalidRequestError,
    InvalidUrlError,
    NetworkError,
    PostProcessingError,
)
from mediagrab.core.ffmpeg import FfmpegPaths
from mediagrab.core.models import (
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    FormatChoice,
    ProgressEvent,
)
from mediagrab.core.postprocessors import FinalPathPP


class FakeEngine:
    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params
        self.processors: list[tuple[PostProcessor, str]] = []
        self.download_action: Callable[[FakeEngine], int] = lambda _: 0
        self.extract_result: Any = {"title": "Test title"}
        self.extract_error: Exception | None = None
        self.urls: list[str] = []
        self.analyzed_url: str | None = None
        self.extract_download: bool | None = None

    def __enter__(self) -> FakeEngine:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def add_post_processor(self, processor: PostProcessor, when: str = "post_process") -> None:
        self.processors.append((processor, when))

    def download(self, urls: list[str]) -> int:
        self.urls = urls
        return self.download_action(self)

    def extract_info(
        self,
        url: str,
        *,
        download: bool,
        process: bool,
        ie_key: str | None = None,
    ) -> object:
        assert process is False
        self.analyzed_url = url
        self.extract_download = download
        if self.extract_error is not None:
            raise self.extract_error
        return self.extract_result

    def finish(self, path: Path) -> None:
        for processor, when in self.processors:
            if when == "after_move":
                assert isinstance(processor, FinalPathPP)
                processor.run({"filepath": str(path)})


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeEngine:
    fake = FakeEngine({})

    def construct(options: dict[str, Any]) -> FakeEngine:
        fake.params = options
        return fake

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", construct)
    monkeypatch.setattr(
        downloader, "get_postprocessor", lambda _: lambda *_args, **_kw: PostProcessor()
    )
    monkeypatch.setattr(
        downloader,
        "ensure_ffmpeg",
        lambda: FfmpegPaths(tmp_path / "tools/ffmpeg", tmp_path / "tools/ffprobe"),
    )
    return fake


def test_metadata_and_analysis_options(engine: FakeEngine) -> None:
    engine.extract_result = {
        "title": "Example",
        "uploader": "Creator",
        "duration": 62.5,
        "thumbnail": "https://example.com/image.jpg",
        "webpage_url": "https://example.com/v",
        "extractor": "test",
        "formats": [
            {"height": 1080, "vcodec": "h264"},
            {"height": 720},
            {"height": 1080},
            {"height": 2160, "vcodec": "none"},
            {"height": -1},
            {"height": True},
            {"height": 720.5},
            None,
        ],
    }
    result = downloader.get_info("  https://example.com/video  ", cookies_browser="firefox")
    assert result.title == "Example"
    assert result.uploader == "Creator"
    assert result.duration == 62.5
    assert result.available_heights == (720, 1080)
    assert result.thumbnail_url == "https://example.com/image.jpg"
    assert result.webpage_url == "https://example.com/v"
    assert result.extractor == "test"
    assert not result.is_playlist and result.entries_count == 1
    assert engine.extract_download is False
    assert engine.analyzed_url == "https://example.com/video"
    for key in ("quiet", "no_warnings", "skip_download", "noplaylist"):
        assert engine.params[key] is True
    assert engine.params["cookiesfrombrowser"] == ("firefox",)


@pytest.mark.parametrize("entries", [[], [{"title": "a"}, {"title": "b"}], iter([{}])])
def test_playlist_count_without_consuming_lazy_entries(engine: FakeEngine, entries: object) -> None:
    engine.extract_result = {"_type": "playlist", "entries": entries}
    info = downloader.get_info("https://example.com/playlist")
    assert info.is_playlist
    assert info.entries_count == (len(entries) if isinstance(entries, list) else None)
    assert info.title == "Untitled media"
    assert info.extractor == "Unknown"
    assert info.duration is None
    assert "cookiesfrombrowser" not in engine.params


def test_explicit_playlist_count_and_metadata_fallbacks(engine: FakeEngine) -> None:
    engine.extract_result = {
        "_type": "multi_video",
        "playlist_count": 30,
        "channel": "Channel",
        "extractor_key": "Test",
        "duration": float("nan"),
    }
    info = downloader.get_info("https://example.com/playlist")
    assert info.entries_count == 30
    assert info.uploader == "Channel"
    assert info.extractor == "Test"
    assert info.duration is None


@pytest.mark.parametrize("result", [None, [], "invalid"])
def test_missing_metadata_is_an_extraction_error(engine: FakeEngine, result: object) -> None:
    engine.extract_result = result
    with pytest.raises(ExtractionError):
        downloader.get_info("https://example.com/video")


def test_analysis_validation_mapping_and_cancellation(engine: FakeEngine) -> None:
    with pytest.raises(InvalidUrlError):
        downloader.get_info("file:///video")
    with pytest.raises(InvalidRequestError):
        downloader.get_info("https://example.com", cookies_browser="safari")  # type: ignore[arg-type]
    engine.extract_error = DownloadError("Unable to download webpage")
    with pytest.raises(NetworkError) as caught:
        downloader.get_info("https://example.com")
    assert caught.value.__cause__ is engine.extract_error
    event = Event()
    event.set()
    with pytest.raises(DownloadCancelledError):
        downloader.get_info("https://example.com", cancel_event=event)


def test_cancellation_after_analysis(engine: FakeEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    event = Event()
    original = engine.extract_info

    def extract(url: str, *, download: bool, process: bool) -> object:
        result = original(url, download=download, process=process)
        event.set()
        return result

    monkeypatch.setattr(engine, "extract_info", extract)
    with pytest.raises(DownloadCancelledError):
        downloader.get_info("https://example.com", cancel_event=event)


@pytest.mark.parametrize("mode", [DownloadMode.VIDEO, DownloadMode.AUDIO])
def test_download_progress_and_final_postprocessed_path(
    engine: FakeEngine,
    tmp_path: Path,
    mode: DownloadMode,
) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path, FormatChoice(mode=mode))
    destination = tmp_path / ("output.mp3" if mode is DownloadMode.AUDIO else "output.mp4")
    events: list[ProgressEvent] = []

    def run(fake: FakeEngine) -> int:
        progress = fake.params["progress_hooks"][0]
        progress(
            {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes_estimate": 100,
                "speed": 20.5,
                "eta": 2,
            }
        )
        progress({"status": "finished", "filename": str(tmp_path / "temporary.webm")})
        fake.params["postprocessor_hooks"][0]({"status": "started", "postprocessor": "Metadata"})
        destination.write_bytes(b"final media")
        fake.finish(destination)
        return 0

    engine.download_action = run
    assert downloader.download(request, events.append, Event()) == destination
    assert engine.urls == [request.url]
    assert [item.status for item in events] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.PROCESSING,
        DownloadStatus.PROCESSING,
        DownloadStatus.FINISHED,
    ]
    assert events[0].percent == 50
    assert events[0].speed_bytes_per_second == 20.5 and events[0].eta_seconds == 2
    assert events[-1].file_path == destination
    assert events[-1].percent == 100
    assert "postprocessors" not in engine.params
    assert engine.params["ignoreerrors"] is False
    if mode is DownloadMode.AUDIO:
        assert engine.params["writethumbnail"] is False


@pytest.mark.parametrize("stage", ["before", "progress", "postprocess", "after"])
def test_download_cancellation(engine: FakeEngine, tmp_path: Path, stage: str) -> None:
    cancellation = Event()
    events: list[ProgressEvent] = []
    request = DownloadRequest("https://example.com/video", tmp_path)
    if stage == "before":
        cancellation.set()

    def run(fake: FakeEngine) -> int:
        cancellation.set()
        if stage == "progress":
            fake.params["progress_hooks"][0]({"status": "downloading"})
        elif stage == "postprocess":
            fake.params["postprocessor_hooks"][0]({"status": "started"})
        return 0

    engine.download_action = run
    with pytest.raises(DownloadCancelledError):
        downloader.download(request, events.append, cancellation)
    assert [item.status for item in events] == [DownloadStatus.CANCELLED]


@pytest.mark.parametrize("exit_code", [0, 1])
def test_no_final_file_is_not_success(engine: FakeEngine, tmp_path: Path, exit_code: int) -> None:
    engine.download_action = lambda _: exit_code
    events: list[ProgressEvent] = []
    with pytest.raises(ExtractionError):
        downloader.download(
            DownloadRequest("https://example.com", tmp_path), events.append, Event()
        )
    assert events[-1].status is DownloadStatus.ERROR


def test_engine_errors_and_missing_ffmpeg_are_reported(
    engine: FakeEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = DownloadError("Connection refused: https://example.com/?token=secret")
    engine.download_action = Mock(side_effect=error)
    events: list[ProgressEvent] = []
    request = DownloadRequest("https://example.com", tmp_path)
    with pytest.raises(NetworkError):
        downloader.download(request, events.append, Event())
    assert "secret" not in events[-1].message
    monkeypatch.setattr(downloader, "ensure_ffmpeg", Mock(side_effect=FfmpegNotFoundError()))
    with pytest.raises(FfmpegNotFoundError):
        downloader.download(request, events.append, Event())
    assert events[-1].status is DownloadStatus.ERROR


def test_callback_failure_is_not_called_recursively(engine: FakeEngine, tmp_path: Path) -> None:
    callback = Mock(side_effect=RuntimeError("consumer failed"))
    engine.download_action = lambda fake: fake.params["progress_hooks"][0]({"status": "finished"})
    with pytest.raises(ExtractionError):
        downloader.download(DownloadRequest("https://example.com", tmp_path), callback, Event())
    callback.assert_called_once()


def test_playlist_returns_last_final_path(engine: FakeEngine, tmp_path: Path) -> None:
    def run(fake: FakeEngine) -> int:
        for name in ("first", "last"):
            path = tmp_path / f"{name}.mp4"
            path.write_bytes(b"media")
            fake.finish(path)
        return 0

    engine.download_action = run
    result = downloader.download(
        DownloadRequest("https://example.com", tmp_path, playlists=True),
        lambda _: None,
        Event(),
    )
    assert result == tmp_path / "last.mp4"


def test_final_path_rejects_temporary_files(engine: FakeEngine, tmp_path: Path) -> None:
    def run(fake: FakeEngine) -> int:
        path = tmp_path / "temporary.webm"
        path.write_bytes(b"temporary")
        fake.finish(path)
        return 0

    engine.download_action = run
    with pytest.raises(PostProcessingError):
        downloader.download(
            DownloadRequest("https://example.com", tmp_path), lambda _: None, Event()
        )


@pytest.mark.parametrize("kind", ["url", "url_transparent"])
def test_analysis_resolves_url_results(
    engine: FakeEngine,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    extractor = Mock(
        side_effect=[
            {
                "_type": kind,
                "url": "https://example.com/target",
                "ie_key": "Test",
                "title": "Wrapper title",
            },
            {"title": "Target title", "formats": [{"height": 1080}]},
        ]
    )
    monkeypatch.setattr(engine, "extract_info", extractor)
    info = downloader.get_info("https://example.com/redirect")
    assert info.title == ("Wrapper title" if kind == "url_transparent" else "Target title")
    assert info.available_heights == (1080,)
    assert extractor.call_args.kwargs == {"ie_key": "Test", "download": False, "process": False}


@pytest.mark.parametrize(
    "result",
    [
        {"_type": "url"},
        {"_type": "url", "url": "https://example.com/loop"},
    ],
)
def test_invalid_or_cyclic_analysis_redirects_are_bounded(
    engine: FakeEngine, result: object
) -> None:
    engine.extract_result = result
    with pytest.raises(ExtractionError):
        downloader.get_info("https://example.com/redirect")


def test_real_engine_analysis_does_not_consume_playlist(monkeypatch: pytest.MonkeyPatch) -> None:
    native_engine = downloader.yt_dlp.YoutubeDL

    class MetadataIE(InfoExtractor):
        _VALID_URL = r"https://media\.example\.test/playlist"

        def _real_extract(self, url: str) -> dict[str, Any]:
            def entries() -> Iterator[dict[str, Any]]:
                yield pytest.fail("Analyze must not enumerate a playlist")

            return {
                "_type": "playlist",
                "id": "test",
                "title": "Playlist",
                "playlist_count": 50,
                "entries": entries(),
            }

    def construct(options: dict[str, Any]) -> yt_dlp.YoutubeDL:
        real = native_engine(options, auto_init=False)
        real.add_info_extractor(MetadataIE())
        return real

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", construct)
    info = downloader.get_info("https://media.example.test/playlist")
    assert info.is_playlist and info.entries_count == 50


def test_unknown_transfer_metrics_and_administrative_hooks_do_not_fake_progress(
    engine: FakeEngine,
    tmp_path: Path,
) -> None:
    events: list[ProgressEvent] = []

    def run(fake: FakeEngine) -> int:
        hook = fake.params["progress_hooks"][0]
        hook({"status": "unknown"})
        hook(
            {
                "status": "downloading",
                "downloaded_bytes": 3,
                "total_bytes": 10,
                "speed": float("nan"),
                "eta": -1,
            }
        )
        fake.params["postprocessor_hooks"][0]({"postprocessor": "OutputGuard"})
        path = tmp_path / "final.mp4"
        path.write_bytes(b"media")
        fake.finish(path)
        return 0

    engine.download_action = run
    downloader.download(DownloadRequest("https://example.com", tmp_path), events.append, Event())
    assert [event.status for event in events] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.FINISHED,
    ]
    assert events[0].percent == 30
    assert events[0].speed_bytes_per_second is None and events[0].eta_seconds is None


def test_cancelling_playlist_preserves_completed_files(engine: FakeEngine, tmp_path: Path) -> None:
    event = Event()
    path = tmp_path / "first.mp4"
    events: list[ProgressEvent] = []

    def run(fake: FakeEngine) -> int:
        path.write_bytes(b"completed entry")
        fake.finish(path)
        event.set()
        fake.params["progress_hooks"][0]({"status": "downloading"})
        return 0

    engine.download_action = run
    with pytest.raises(DownloadCancelledError):
        downloader.download(
            DownloadRequest("https://example.com", tmp_path, playlists=True),
            events.append,
            event,
        )
    assert path.read_bytes() == b"completed entry"
    assert events[-1].status is DownloadStatus.CANCELLED
    assert all(item.status is not DownloadStatus.FINISHED for item in events)
