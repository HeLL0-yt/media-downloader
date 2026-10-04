"""Immutable download settings, metadata, and progress snapshots."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Literal

from mediagrab.core.errors import InvalidRequestError
from mediagrab.core.validators import validate_url

VIDEO_HEIGHTS: tuple[int, ...] = (2160, 1440, 1080, 720, 480, 360)
AUDIO_BITRATES: tuple[int, ...] = (320, 192, 128)
type Browser = Literal["chrome", "firefox", "edge"]


class DownloadMode(StrEnum):
    """Select video with audio or an audio-only MP3."""

    VIDEO = "video"
    AUDIO = "audio"


class DownloadStatus(StrEnum):
    """Queue and progress states shared by the core and desktop layers."""

    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING = "merging/converting"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Extracted metadata without dependence on a GUI or yt-dlp objects.

    Attributes:
        title: Display title.
        webpage_url: Canonical media page URL.
        extractor: Engine extractor name.
        uploader: Uploader name, when available.
        duration: Duration in seconds, when available.
        thumbnail_url: Thumbnail URL, when available.
        is_playlist: Whether this result describes a playlist.
        entries_count: Entry count when known; None denotes an unknown count.
        available_heights: Sorted unique heights as an immutable tuple.
    """

    title: str
    webpage_url: str = field(repr=False)
    extractor: str
    uploader: str | None = None
    duration: float | None = None
    thumbnail_url: str | None = field(default=None, repr=False)
    is_playlist: bool = False
    entries_count: int | None = 1
    available_heights: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Normalize video heights into a sorted, immutable collection."""
        if any(type(height) is not int or height <= 0 for height in self.available_heights):
            raise InvalidRequestError("Video heights must be positive integers.")
        object.__setattr__(self, "available_heights", tuple(sorted(set(self.available_heights))))


@dataclass(frozen=True, slots=True)
class FormatChoice:
    """Validated format settings; None represents the best available quality.

    Attributes:
        mode: Video or audio-only mode.
        max_height: Video height ceiling or None for no height limit.
        audio_bitrate: MP3 bitrate in kbps or None for best variable bitrate.
    """

    mode: DownloadMode = DownloadMode.VIDEO
    max_height: int | None = None
    audio_bitrate: int | None = None

    def __post_init__(self) -> None:
        """Reject invalid modes, heights, and bitrates at the core boundary."""
        if not isinstance(self.mode, DownloadMode):
            raise InvalidRequestError("Select video or audio mode.")
        if self.max_height is not None and (
            type(self.max_height) is not int or self.max_height <= 0
        ):
            raise InvalidRequestError("Select a positive integer maximum video height.")
        if self.audio_bitrate is not None and (
            type(self.audio_bitrate) is not int or self.audio_bitrate not in AUDIO_BITRATES
        ):
            raise InvalidRequestError("Select best, 320, 192, or 128 kbps audio quality.")


@dataclass(frozen=True, slots=True)
class DownloadRequest:
    """A validated download request that can be shared safely with a worker.

    Attributes:
        url: Validated media URL, omitted from repr to protect signed URLs.
        output_dir: Destination; the worker must prepare it before downloading.
        format: Requested mode and quality.
        playlists: Enable complete playlists; defaults to single-video behavior.
        prefer_compatibility: Prefer H.264/AAC within the selected resolution.
        embed_thumbnail: Attempt to embed an MP3 cover image.
        cookies_browser: Opt-in browser session access, disabled by default.
    """

    url: str = field(repr=False)
    output_dir: Path
    format: FormatChoice = field(default_factory=FormatChoice)
    playlists: bool = False
    prefer_compatibility: bool = True
    embed_thumbnail: bool = True
    cookies_browser: Browser | None = None

    def __post_init__(self) -> None:
        """Validate settings and strip surrounding whitespace from the URL."""
        object.__setattr__(self, "url", validate_url(self.url))
        if not isinstance(self.output_dir, Path) or not isinstance(self.format, FormatChoice):
            raise InvalidRequestError("Provide a destination Path and a FormatChoice.")
        for name in ("playlists", "prefer_compatibility", "embed_thumbnail"):
            if type(getattr(self, name)) is not bool:
                raise InvalidRequestError(f"{name} must be true or false.")
        if self.cookies_browser not in (None, "chrome", "firefox", "edge"):
            raise InvalidRequestError("Select Chrome, Firefox, Edge, or no browser cookies.")


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """A plain callback payload; byte counts refer to the current media transfer.

    Attributes:
        status: Download or processing stage.
        downloaded_bytes: Bytes received for the current transfer.
        total_bytes: Transfer size, or None when the engine does not know it.
        speed_bytes_per_second: Current transfer speed, when known.
        eta_seconds: Estimated remaining transfer time, when known.
        file_path: Current or final media path, when known.
        message: Safe user-facing message, without raw engine errors or URLs.
    """

    status: DownloadStatus
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed_bytes_per_second: float | None = None
    eta_seconds: float | None = None
    file_path: Path | None = None
    message: str | None = None

    @property
    def percent(self) -> float | None:
        """Return bounded percentage, or None when the transfer size is unknown."""
        if self.status is DownloadStatus.FINISHED:
            return 100.0
        if self.total_bytes is None or self.total_bytes <= 0:
            return None
        return min(100.0, max(0.0, 100.0 * self.downloaded_bytes / self.total_bytes))


type ProgressCallback = Callable[[ProgressEvent], None]
