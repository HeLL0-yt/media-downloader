"""Every supported quality, playlist behavior, and actual yt-dlp option parsing."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from yt_dlp import YoutubeDL

from mediagrab.core.ffmpeg import FfmpegPaths
from mediagrab.core.models import (
    AUDIO_BITRATES,
    VIDEO_HEIGHTS,
    Browser,
    DownloadMode,
    DownloadRequest,
    FormatChoice,
)
from mediagrab.core.options import build_options


@pytest.fixture
def tools(tmp_path: Path) -> FfmpegPaths:
    directory = tmp_path / "tools"
    return FfmpegPaths(directory / "ffmpeg.exe", directory / "ffprobe.exe")


@pytest.mark.parametrize("height", [None, *VIDEO_HEIGHTS])
@pytest.mark.parametrize("playlists", [False, True])
@pytest.mark.parametrize("compatibility", [False, True])
def test_video_options_for_each_height_and_playlist_setting(
    height: int | None,
    playlists: bool,
    compatibility: bool,
    tmp_path: Path,
    tools: FfmpegPaths,
) -> None:
    request = DownloadRequest(
        "https://example.com/video",
        tmp_path,
        format=FormatChoice(max_height=height),
        playlists=playlists,
        prefer_compatibility=compatibility,
    )
    options = build_options(request, tools)
    ceiling = "" if height is None else f"[height<={height}]"
    assert options["format"] == f"bestvideo*{ceiling}+bestaudio/best{ceiling}"
    assert options["merge_output_format"] == "mp4"
    assert options["final_ext"] == "mp4"
    assert options["postprocessors"] == [
        {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"},
        {"key": "FFmpegMetadata"},
    ]
    assert options["noplaylist"] is not playlists
    assert ("playlist_items" not in options) if playlists else options["playlist_items"] == "1"
    if compatibility:
        assert options["format_sort"] == ["res", "vcodec:h264", "acodec:aac"]
    else:
        assert "format_sort" not in options


@pytest.mark.parametrize("bitrate", [None, *AUDIO_BITRATES])
@pytest.mark.parametrize("embed_thumbnail", [False, True])
@pytest.mark.parametrize("playlists", [False, True])
def test_audio_options_for_each_bitrate_thumbnail_and_playlist_setting(
    bitrate: int | None,
    embed_thumbnail: bool,
    playlists: bool,
    tmp_path: Path,
    tools: FfmpegPaths,
) -> None:
    request = DownloadRequest(
        "https://example.com/video",
        tmp_path,
        format=FormatChoice(DownloadMode.AUDIO, audio_bitrate=bitrate),
        embed_thumbnail=embed_thumbnail,
        playlists=playlists,
    )
    options = build_options(request, tools)
    assert options["format"] == "bestaudio/best"
    assert options["final_ext"] == "mp3"
    assert options["postprocessors"][0] == {
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "0" if bitrate is None else str(bitrate),
    }
    assert options["postprocessors"][1] == {"key": "FFmpegMetadata"}
    assert options["writethumbnail"] is embed_thumbnail
    assert (len(options["postprocessors"]) == 3) is embed_thumbnail
    if embed_thumbnail:
        assert options["postprocessors"][-1] == {
            "key": "EmbedThumbnail",
            "already_have_thumbnail": False,
        }
    assert options["noplaylist"] is not playlists
    assert "merge_output_format" not in options
    assert "format_sort" not in options


def test_common_options_and_builder_have_no_filesystem_side_effects(
    tmp_path: Path, tools: FfmpegPaths
) -> None:
    directory = tmp_path / "not-created"
    request = DownloadRequest("https://example.com/video", directory)
    options = build_options(request, tools)
    expected = {
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
        "restrictfilenames": False,
        "ffmpeg_location": str(tools.location),
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 20,
        "concurrent_fragment_downloads": 4,
        "noprogress": True,
        "ignoreerrors": False,
        "cachedir": False,
        "progress_hooks": [],
        "postprocessor_hooks": [],
    }
    assert all(options[name] == value for name, value in expected.items())
    assert options["outtmpl"] == f"{directory.as_posix()}/%(title).150B [%(id)s].%(ext)s"
    assert "cookiesfrombrowser" not in options
    assert not directory.exists()
    assert not tools.location.exists()


@pytest.mark.parametrize("browser", ["chrome", "firefox", "edge"])
def test_browser_cookies_are_an_opt_in_tuple(
    browser: Browser, tmp_path: Path, tools: FfmpegPaths
) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path, cookies_browser=browser)
    assert build_options(request, tools)["cookiesfrombrowser"] == (browser,)


def test_callbacks_and_nested_configuration_are_fresh(tmp_path: Path, tools: FfmpegPaths) -> None:
    def hook(payload: dict[str, Any]) -> None:
        raise AssertionError("The options builder must not invoke callbacks")

    request = DownloadRequest("https://example.com/video", tmp_path)
    callbacks = [hook]
    first = build_options(request, tools, progress_hooks=callbacks, postprocessor_hooks=callbacks)
    second = build_options(request, tools, progress_hooks=callbacks)
    assert first["progress_hooks"] == callbacks
    assert first["postprocessor_hooks"] == callbacks
    assert first["progress_hooks"] is not callbacks
    first["progress_hooks"].clear()
    first["postprocessors"][0]["preferedformat"] = "webm"
    assert len(callbacks) == 1
    assert len(second["progress_hooks"]) == 1
    assert second["postprocessors"][0]["preferedformat"] == "mp4"


@pytest.mark.parametrize("mode", [DownloadMode.VIDEO, DownloadMode.AUDIO])
def test_installed_ytdlp_accepts_built_postprocessors_and_format_selector(
    mode: DownloadMode, tmp_path: Path, tools: FfmpegPaths
) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path, format=FormatChoice(mode))
    options = build_options(request, tools)
    with YoutubeDL(options) as engine:
        assert callable(engine.build_format_selector(options["format"]))


@pytest.mark.parametrize("title", ["../../escape", "CON", "a:b*?c\x00\n", "名字" * 200])
def test_real_engine_sanitizes_names_without_path_traversal(
    title: str, tmp_path: Path, tools: FfmpegPaths
) -> None:
    # The destination contains literal template syntax and must remain literal.
    directory = tmp_path / "100% %(id)s"
    request = DownloadRequest("https://example.com/video", directory)
    with YoutubeDL(build_options(request, tools)) as engine:
        filename = engine.prepare_filename({"title": title, "id": "../escape", "ext": "mp4"})
    assert filename is not None
    path = Path(filename)
    assert path.parent.resolve() == directory.resolve()
    assert path.suffix == ".mp4"
    assert not any(character in path.name for character in '<>:"/\\|?*\x00\n')


def test_compatibility_prefers_codecs_without_reducing_resolution(
    tmp_path: Path, tools: FfmpegPaths
) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path)
    formats: list[dict[str, Any]] = [
        {"format_id": "av1-1080", "vcodec": "av01", "height": 1080, "width": 1920},
        {"format_id": "h264-1080", "vcodec": "avc1", "height": 1080, "width": 1920},
        {"format_id": "av1-2160", "vcodec": "av01", "height": 2160, "width": 3840},
    ]
    for item in formats:
        item.update(url="https://example.com/video", acodec="none", ext="mp4")
    with YoutubeDL(build_options(request, tools)) as engine:
        info: dict[str, Any] = {"formats": formats}
        engine.sort_formats(info)
    assert [item["format_id"] for item in info["formats"]] == [
        "av1-1080",
        "h264-1080",
        "av1-2160",
    ]


def test_compatibility_can_be_disabled(tmp_path: Path, tools: FfmpegPaths) -> None:
    request = DownloadRequest("https://example.com/video", tmp_path)
    assert "format_sort" not in build_options(replace(request, prefer_compatibility=False), tools)
