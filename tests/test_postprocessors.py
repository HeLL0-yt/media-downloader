"""Conversion decisions, output boundaries, and nonfatal thumbnail failures."""

import io
import json
import subprocess
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest
from yt_dlp.utils import DownloadCancelled

from mediagrab.core import postprocessors as pp
from mediagrab.core.errors import DownloadCancelledError, OutputDirectoryError, PostProcessingError
from mediagrab.core.ffmpeg import FfmpegPaths


@pytest.fixture
def tools(tmp_path: Path) -> FfmpegPaths:
    return FfmpegPaths(tmp_path / "tools/ffmpeg", tmp_path / "tools/ffprobe")


@pytest.mark.parametrize("name", ["../escaped.mp4", "sub/../../escaped.mp4"])
def test_output_boundary_rejects_traversal(tmp_path: Path, name: str) -> None:
    with pytest.raises(OutputDirectoryError):
        pp.bounded_path(tmp_path / name, tmp_path)
    with pytest.raises(OutputDirectoryError):
        pp.bounded_path(tmp_path, tmp_path)


def test_resolution_failure_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "resolve", Mock(side_effect=OSError("failed")))
    with pytest.raises(OutputDirectoryError):
        pp.bounded_path(tmp_path / "file", tmp_path)


def test_output_guard_and_cancel(tmp_path: Path) -> None:
    event = Event()
    processor = pp.OutputGuardPP(tmp_path, "mp4", event)
    engine = Mock()
    engine._postprocessor_hooks = []
    engine._copy_infodict = dict
    engine.params = {}
    engine.prepare_filename.return_value = str(tmp_path / "video.webm")
    processor.set_downloader(engine)
    assert processor.run({}) == ([], {})
    engine.prepare_filename.return_value = None
    with pytest.raises(OutputDirectoryError):
        processor.run({})
    event.set()
    with pytest.raises(DownloadCancelled):
        processor.run({})


@pytest.mark.parametrize("compatibility", [True, False])
def test_split_streams_use_a_codec_safe_intermediate_only_for_compatibility(
    tmp_path: Path,
    compatibility: bool,
) -> None:
    engine = Mock()
    engine._postprocessor_hooks = []
    engine._copy_infodict = dict
    engine.params = {}
    engine.prepare_filename.return_value = str(tmp_path / "media.mp4")
    processor = pp.OutputGuardPP(tmp_path, "mp4", Event(), compatibility=compatibility)
    processor.set_downloader(engine)
    info = {"ext": "mp4", "requested_formats": [{"vcodec": "vp8"}, {"acodec": "opus"}]}
    processor.run(info)
    assert info["ext"] == ("mkv" if compatibility else "mp4")


@pytest.mark.parametrize("value", [None, "missing.mp4", "empty.mp4", "temporary.part"])
def test_final_collector_requires_a_nonempty_final_file(tmp_path: Path, value: str | None) -> None:
    processor = pp.FinalPathPP(tmp_path, "mp4", Event())
    if value in {"empty.mp4", "temporary.part"}:
        (tmp_path / value).touch()
    info = {} if value is None else {"filepath": str(tmp_path / value)}
    with pytest.raises(PostProcessingError):
        processor.run(info)
    assert not processor.paths


@pytest.mark.parametrize("payload", ["{}", "not json", '{"streams": {}}', '{"streams": [null]}'])
def test_probe_rejects_invalid_data(
    tmp_path: Path,
    tools: FfmpegPaths,
    payload: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pp, "run_process", Mock(return_value=subprocess.CompletedProcess([], 0, payload))
    )
    with pytest.raises(PostProcessingError):
        pp.probe_media(tmp_path / "video.mp4", tools, Event())


def test_probe_native_failure(
    tmp_path: Path, tools: FfmpegPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pp, "run_process", Mock(side_effect=subprocess.TimeoutExpired([], 20)))
    with pytest.raises(PostProcessingError):
        pp.probe_media(tmp_path / "video.mp4", tools, Event())


@pytest.mark.parametrize(
    (
        "extension",
        "codec",
        "pixel_format",
        "audio_codec",
        "compatibility",
        "video_encoder",
        "audio_encoder",
    ),
    [
        ("mp4", "h264", "yuv420p", "aac", True, None, None),
        ("mp4", "vp9", "yuv420p", "opus", False, None, None),
        ("mp4", "av1", "yuv420p10le", "opus", True, "libx264", "aac"),
        ("mp4", "h264", "yuv444p", "aac", True, "libx264", "copy"),
        ("webm", "vp9", "yuv420p", "opus", True, "libx264", "aac"),
        ("mkv", "h264", "yuv420p", "aac", True, "copy", "copy"),
        ("mkv", "vp9", "yuv420p", "opus", False, "copy", "copy"),
        ("mp4", "h264", "yuv420p", None, True, None, None),
    ],
)
def test_video_conversion_only_encodes_incompatible_streams(
    tmp_path: Path,
    tools: FfmpegPaths,
    monkeypatch: pytest.MonkeyPatch,
    extension: str,
    codec: str,
    pixel_format: str,
    audio_codec: str | None,
    compatibility: bool,
    video_encoder: str | None,
    audio_encoder: str | None,
) -> None:
    source = tmp_path / f"source.{extension}"
    source.write_bytes(b"source")
    streams = [{"codec_type": "video", "codec_name": codec, "pix_fmt": pixel_format}]
    if audio_codec is not None:
        streams.append({"codec_type": "audio", "codec_name": audio_codec})
    calls: list[list[str]] = []

    def run(
        args: list[str], *, timeout: float, cancel_event: Event
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[0] == str(tools.ffprobe):
            assert timeout == 20
            return subprocess.CompletedProcess(args, 0, json.dumps({"streams": streams}))
        assert timeout == 86400
        Path(args[-1]).write_bytes(b"converted")
        return subprocess.CompletedProcess(args, 0, "")

    monkeypatch.setattr(pp, "run_process", run)
    processor = pp.VideoOutputPP(tools, tmp_path, Event(), compatibility)
    info = {"filepath": str(source), "ext": extension}
    deleted, result = processor.run(info)
    if video_encoder is None:
        assert len(calls) == 1
        assert not deleted
        assert result["filepath"] == str(source)
    else:
        command = calls[-1]
        assert command[command.index("-c:v") + 1] == video_encoder
        assert command[command.index("-c:a") + 1] == audio_encoder
        assert "-movflags" in command
        if video_encoder == "libx264":
            assert command[command.index("-vf") + 1] == "pad=ceil(iw/2)*2:ceil(ih/2)*2"
        assert Path(result["filepath"]).read_bytes() == b"converted"
        assert result["ext"] == "mp4"
        assert deleted == ([str(source)] if extension != "mp4" else [])
    assert not list(tmp_path.glob(".mediagrab-*"))


def test_partial_artwork_copy_cannot_replace_original_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "audio.mp3"
    source.write_bytes(b"complete MP3")
    engine = Mock()
    engine._postprocessor_hooks = []
    engine._copy_infodict = dict
    engine.params = {}
    engine.urlopen.return_value = io.BytesIO(b"image")

    def partial_copy(original: Path, copy: Path) -> None:
        copy.write_bytes(b"partial")
        raise OSError("out of disk space")

    monkeypatch.setattr(pp.shutil, "copyfile", partial_copy)
    warning = Mock()
    processor = pp.OptionalThumbnailPP(Event(), tmp_path, warning)
    processor.set_downloader(engine)
    info = {"filepath": str(source), "thumbnails": [{"url": "https://example.com/image.jpg"}]}
    assert processor.run(info) == ([], info)
    assert source.read_bytes() == b"complete MP3"
    warning.assert_called_once()


def test_artwork_cleanup_failure_is_logged_without_aborting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / ".mediagrab-artwork-owned.jpg"
    monkeypatch.setattr(Path, "unlink", Mock(side_effect=PermissionError("locked file")))
    pp.OptionalThumbnailPP(Event(), tmp_path)._cleanup(None, path)
    assert "could not be removed" in caplog.text


def test_thumbnail_backup_failure_is_nonfatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "audio.mp3"
    source.write_bytes(b"MP3")
    engine = Mock()
    engine._postprocessor_hooks = []
    engine._copy_infodict = dict
    engine.params = {}
    engine.urlopen.return_value = io.BytesIO(b"image")
    monkeypatch.setattr(pp.shutil, "copyfile", Mock(side_effect=OSError("unwritable")))
    processor = pp.OptionalThumbnailPP(Event(), tmp_path)
    processor.set_downloader(engine)
    info = {"filepath": str(source), "thumbnails": [{"url": "https://example.com/image.unknown"}]}
    assert processor.run(info) == ([], info)
    assert source.read_bytes() == b"MP3"
    engine.report_warning.assert_called_once()
    assert not list(tmp_path.glob(".mediagrab-*"))


@pytest.mark.parametrize("failure", ["no_video", "conversion", "empty", "cancel"])
def test_video_processing_failure_preserves_source_and_cleans_temp(
    tmp_path: Path,
    tools: FfmpegPaths,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original")
    event = Event()
    streams = [] if failure == "no_video" else [{"codec_type": "video", "codec_name": "vp9"}]
    monkeypatch.setattr(pp, "probe_media", lambda *_: streams)

    def run(args: list[str], **kwargs: object) -> None:
        if failure == "cancel":
            raise DownloadCancelledError()
        if failure == "conversion":
            raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(pp, "run_process", run)
    expected = DownloadCancelledError if failure == "cancel" else PostProcessingError
    with pytest.raises(expected):
        pp.VideoOutputPP(tools, tmp_path, event, True).run({"filepath": str(source)})
    assert source.read_bytes() == b"original"
    assert not list(tmp_path.glob(".mediagrab-*"))


@pytest.mark.parametrize("outcome", ["success", "embedding", "network", "cancel", "oversize"])
def test_optional_artwork_preserves_audio_and_cleans_owned_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    source = tmp_path / "audio.mp3"
    source.write_bytes(b"converted MP3")
    event = Event()
    engine = Mock()
    engine.params = {}
    engine._postprocessor_hooks = []
    engine._copy_infodict = dict
    engine.urlopen.return_value = io.BytesIO(b"image" if outcome != "oversize" else b"a" * 10485761)
    if outcome == "network":
        engine.urlopen.side_effect = OSError("network failed")

    class Embedding:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def run(self, info: dict[str, object]) -> tuple[list[str], dict[str, object]]:
            Path(str(info["filepath"])).write_bytes(b"embedded MP3")
            if outcome == "embedding":
                raise RuntimeError("embedding failed")
            if outcome == "cancel":
                event.set()
            return [], info

    monkeypatch.setattr(pp, "EmbedThumbnailPP", Embedding)
    processor = pp.OptionalThumbnailPP(event, tmp_path)
    processor.set_downloader(engine)
    info = {"filepath": str(source), "thumbnails": [{"url": "https://example.com/image.webp"}]}
    if outcome == "cancel":
        with pytest.raises(DownloadCancelled):
            processor.run(info)
    else:
        deleted, result = processor.run(info)
        assert deleted == [] and result is info
        if outcome != "success":
            engine.report_warning.assert_called_once()
    assert source.read_bytes() == (b"embedded MP3" if outcome == "success" else b"converted MP3")
    assert not list(tmp_path.glob(".mediagrab-*"))


def test_optional_artwork_without_thumbnail_is_a_noop(tmp_path: Path) -> None:
    info = {"filepath": str(tmp_path / "audio.mp3")}
    assert pp.OptionalThumbnailPP(Event(), tmp_path).run(info) == ([], info)
