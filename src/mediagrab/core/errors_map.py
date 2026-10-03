"""Translate engine failures into safe application errors."""

import errno
from urllib.error import URLError

from yt_dlp import utils
from yt_dlp.cookies import CookieLoadError
from yt_dlp.networking.exceptions import RequestError

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

_MESSAGE_RULES: tuple[tuple[type[MediaGrabError], tuple[str, ...]], ...] = (
    (DrmProtectedError, ("drm protected", "drm-protected", "protected by drm", "has drm")),
    (PrivateVideoError, ("private video", "video is private", "private account")),
    (
        AgeRestrictionError,
        ("age-restricted", "age restricted", "confirm your age", "age verification"),
    ),
    (
        GeoBlockedError,
        (
            "not available in your country",
            "not available in your region",
            "geo-restricted",
            "geo blocked",
            "geographic restriction",
        ),
    ),
    (
        LoginRequiredError,
        (
            "login required",
            "log in",
            "sign in",
            "login to",
            "authentication required",
            "cookies are required",
            "could not copy chrome cookie",
            "failed to decrypt",
        ),
    ),
    (UnsupportedUrlError, ("unsupported url", "no suitable extractor")),
    (FormatUnavailableError, ("requested format is not available", "no video formats found")),
    (
        FfmpegNotFoundError,
        (
            "ffmpeg not found",
            "ffprobe not found",
            "ffmpeg is not installed",
            "ffprobe and ffmpeg not found",
            "ffmpeg could not be found",
        ),
    ),
    (
        NetworkError,
        (
            "timed out",
            "timeout",
            "connection refused",
            "connection reset",
            "network is unreachable",
            "name resolution",
            "getaddrinfo failed",
            "unable to download",
            "http error",
            "certificate verify failed",
        ),
    ),
    (PostProcessingError, ("postprocessing:", "post-processing failed", "conversion failed")),
)


def _chain(error: Exception) -> list[Exception]:
    result: list[Exception] = []
    current: Exception | None = error
    while current is not None and all(current is not item for item in result):
        result.append(current)
        nested = current.__cause__ or current.__context__
        exc_info = getattr(current, "exc_info", None)
        if nested is None and isinstance(exc_info, tuple) and len(exc_info) == 3:
            nested = exc_info[1]
        current = nested if isinstance(nested, Exception) else None
    return result


def map_error(error: Exception) -> MediaGrabError:
    """Map an exception without exposing the engine's raw diagnostic message.

    Typed causes take priority. Message matching is a fallback for extractors
    that wrap failures in DownloadError; unknown diagnostics remain generic.

    Args:
        error: Original failure, including an optional chained engine cause.

    Returns:
        Typed error with a safe default message, or an existing application error.
    """
    chain = _chain(error)
    for item in chain:
        if isinstance(item, MediaGrabError):
            return item
        if isinstance(item, utils.DownloadCancelled):
            return DownloadCancelledError()
        if isinstance(item, utils.GeoRestrictedError):
            return GeoBlockedError()
        if isinstance(item, utils.UnsupportedError):
            return UnsupportedUrlError()
        if isinstance(item, CookieLoadError):
            return LoginRequiredError()
        if isinstance(item, OSError) and item.errno in {
            errno.EACCES,
            errno.EPERM,
            errno.ENOSPC,
            errno.EROFS,
            errno.EDQUOT,
        }:
            return OutputDirectoryError()

    message = " ".join(str(item).lower() for item in chain)
    for error_type, patterns in _MESSAGE_RULES:
        if any(pattern in message for pattern in patterns):
            return error_type()
    if any(
        isinstance(item, (TimeoutError, ConnectionError, URLError, RequestError)) for item in chain
    ):
        return NetworkError()
    if any(isinstance(item, utils.PostProcessingError) for item in chain):
        return PostProcessingError()
    return ExtractionError()
