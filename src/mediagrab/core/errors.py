"""Typed application errors with safe, user-facing default messages."""

from typing import ClassVar


class MediaGrabError(Exception):
    """Base class for failures that can be presented to the user."""

    default_message: ClassVar[str] = "MediaGrab could not complete the operation."

    def __init__(self, message: str | None = None) -> None:
        """Initialize the error without including sensitive input by default.

        Args:
            message: Safe message to show, or None to use the class default.
        """
        super().__init__(self.default_message if message is None else message)


class InvalidUrlError(MediaGrabError):
    """The input is not an accepted HTTP or HTTPS URL."""

    default_message: ClassVar[str] = "Enter a valid HTTP or HTTPS media URL."


class InvalidRequestError(MediaGrabError):
    """A download setting is invalid."""

    default_message: ClassVar[str] = "Check the selected download settings."


class OutputDirectoryError(MediaGrabError):
    """The output directory cannot be created or written."""

    default_message: ClassVar[str] = (
        "The output folder cannot be created or written. "
        "Choose another folder or check its permissions."
    )


class FfmpegNotFoundError(MediaGrabError):
    """A complete FFmpeg and ffprobe installation was not found."""

    default_message: ClassVar[str] = (
        "FFmpeg and ffprobe were not found together. Install both executables "
        "in one folder and add that folder to PATH, or place them next to MediaGrab. "
        "Install the FFmpeg binaries, not the Python ffmpeg package."
    )


class FfmpegVersionError(MediaGrabError):
    """An FFmpeg executable cannot run or return a valid version banner."""

    default_message: ClassVar[str] = (
        "FFmpeg or ffprobe could not run. Reinstall a working FFmpeg build "
        "for this computer and check executable permissions."
    )


class DownloadCancelledError(MediaGrabError):
    """The user cancelled a download."""

    default_message: ClassVar[str] = "Download cancelled."


class ExtractionError(MediaGrabError):
    """The engine cannot extract the requested media."""

    default_message: ClassVar[str] = "The media could not be analyzed or downloaded."


class NetworkError(MediaGrabError):
    """A network connection failed."""

    default_message: ClassVar[str] = "A network request failed. Check your connection and retry."


class LoginRequiredError(ExtractionError):
    """The platform requires an authenticated session."""

    default_message: ClassVar[str] = (
        "This media requires login. Sign in using your browser, then enable "
        "cookies from that browser in MediaGrab settings."
    )


class GeoBlockedError(ExtractionError):
    """The platform does not make the media available in this region."""

    default_message: ClassVar[str] = "This media is not available in your region."


class PrivateVideoError(ExtractionError):
    """The requested media is private."""

    default_message: ClassVar[str] = (
        "This media is private. Access requires the owner's permission."
    )


class AgeRestrictionError(ExtractionError):
    """The platform requires age verification."""

    default_message: ClassVar[str] = (
        "This media is age restricted. Complete the platform's age verification "
        "in your browser before using browser cookies."
    )


class UnsupportedUrlError(ExtractionError):
    """The engine does not support the requested URL."""

    default_message: ClassVar[str] = "This URL is not supported by the download engine."


class DrmProtectedError(ExtractionError):
    """The media is protected by DRM and cannot be downloaded by MediaGrab."""

    default_message: ClassVar[str] = "This media is DRM protected. MediaGrab does not bypass DRM."


class PostProcessingError(MediaGrabError):
    """Media merging or conversion failed."""

    default_message: ClassVar[str] = (
        "Media conversion failed. Check FFmpeg and available disk space."
    )
