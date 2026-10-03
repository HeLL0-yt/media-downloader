"""Safe error classifications for typed failures and extractor diagnostics."""

import errno
from urllib.error import URLError

import pytest
from yt_dlp.cookies import CookieLoadError
from yt_dlp.utils import (
    DownloadCancelled,
    DownloadError,
    ExtractorError,
    GeoRestrictedError,
    UnsupportedError,
)
from yt_dlp.utils import (
    PostProcessingError as EnginePostProcessingError,
)

from mediagrab.core.errors import (
    AgeRestrictionError,
    DownloadCancelledError,
    DrmProtectedError,
    ExtractionError,
    FfmpegNotFoundError,
    FormatUnavailableError,
    GeoBlockedError,
    LoginRequiredError,
    MediaGrabError,
    NetworkError,
    OutputDirectoryError,
    PostProcessingError,
    PrivateVideoError,
    UnsupportedUrlError,
)
from mediagrab.core.errors_map import map_error


@pytest.mark.parametrize("engine_type", [DownloadError, ExtractorError])
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Private video. Sign in if you have access", PrivateVideoError),
        ("This video is private", PrivateVideoError),
        ("Sign in to confirm your age", AgeRestrictionError),
        ("This video is age-restricted", AgeRestrictionError),
        ("Video not available in your country", GeoBlockedError),
        ("Content not available in your region", GeoBlockedError),
        ("Login required", LoginRequiredError),
        ("Please log in to access this media", LoginRequiredError),
        ("Sign in to confirm you're not a bot", LoginRequiredError),
        ("Could not copy Chrome cookie database", LoginRequiredError),
        ("Unsupported URL", UnsupportedUrlError),
        ("Requested format is not available", FormatUnavailableError),
        ("ffmpeg not found", FfmpegNotFoundError),
        ("ffprobe and ffmpeg not found", FfmpegNotFoundError),
        ("Unable to download webpage: HTTP Error 403", NetworkError),
        ("Connection reset by peer", NetworkError),
        ("getaddrinfo failed", NetworkError),
        ("The media is DRM protected", DrmProtectedError),
        ("Postprocessing: Conversion failed", PostProcessingError),
        ("Unrecognized extractor problem", ExtractionError),
    ],
)
def test_engine_messages(
    message: str, expected: type[MediaGrabError], engine_type: type[Exception]
) -> None:
    error = engine_type(f"{message}: https://example.com/?token=secret")
    mapped = map_error(error)
    assert type(mapped) is expected
    assert "secret" not in str(mapped)
    assert "https://" not in str(mapped)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (DownloadCancelled(), DownloadCancelledError),
        (GeoRestrictedError("blocked"), GeoBlockedError),
        (UnsupportedError("https://example.com"), UnsupportedUrlError),
        (CookieLoadError("unavailable browser database"), LoginRequiredError),
        (TimeoutError(), NetworkError),
        (ConnectionError(), NetworkError),
        (URLError("offline"), NetworkError),
        (EnginePostProcessingError("failed"), PostProcessingError),
        (OSError(errno.ENOSPC, "disk full"), OutputDirectoryError),
        (OSError(errno.EACCES, "access denied"), OutputDirectoryError),
    ],
)
def test_typed_failures(error: Exception, expected: type[MediaGrabError]) -> None:
    assert type(map_error(error)) is expected


def test_preserves_application_error_and_follows_engine_exc_info() -> None:
    original = OutputDirectoryError()
    wrapper = DownloadError("download failed", (type(original), original, None))
    assert map_error(wrapper) is original
    assert map_error(original) is original


def test_cause_cycles_terminate_and_unknowns_remain_generic() -> None:
    first = RuntimeError("first")
    second = RuntimeError("second")
    first.__cause__ = second
    second.__cause__ = first
    assert type(map_error(first)) is ExtractionError


def test_explicit_geo_diagnostic_precedes_network_cause() -> None:
    error = DownloadError("This content is not available in your country")
    error.__cause__ = URLError("HTTP Error 403")
    assert type(map_error(error)) is GeoBlockedError
