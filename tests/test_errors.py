"""Public error defaults and useful exception categories."""

import pytest

from mediagrab.core import errors


@pytest.mark.parametrize(
    "error_type",
    [
        errors.MediaGrabError,
        errors.InvalidUrlError,
        errors.InvalidRequestError,
        errors.OutputDirectoryError,
        errors.FfmpegNotFoundError,
        errors.FfmpegVersionError,
        errors.DownloadCancelledError,
        errors.ExtractionError,
        errors.NetworkError,
        errors.LoginRequiredError,
        errors.GeoBlockedError,
        errors.PrivateVideoError,
        errors.AgeRestrictionError,
        errors.UnsupportedUrlError,
        errors.DrmProtectedError,
        errors.PostProcessingError,
    ],
)
def test_typed_errors_have_safe_defaults(error_type: type[errors.MediaGrabError]) -> None:
    error = error_type()
    assert isinstance(error, errors.MediaGrabError)
    assert str(error) == error_type.default_message
    assert str(error)


def test_error_can_preserve_an_explicit_safe_message() -> None:
    assert str(errors.MediaGrabError("Choose another folder.")) == "Choose another folder."


def test_platform_access_errors_are_extraction_errors() -> None:
    for error_type in (
        errors.LoginRequiredError,
        errors.GeoBlockedError,
        errors.PrivateVideoError,
        errors.AgeRestrictionError,
        errors.UnsupportedUrlError,
        errors.DrmProtectedError,
    ):
        assert isinstance(error_type(), errors.ExtractionError)
