"""Offline checks for the download engine's browser impersonation support."""

import logging
from dataclasses import dataclass

import yt_dlp
from yt_dlp.version import __version__ as YT_DLP_VERSION

from mediagrab.core.logging_utils import EngineLogger, log_exception

_LOGGER = logging.getLogger(__name__)
_INSTALL_INSTRUCTION = (
    "Reinstall MediaGrab's runtime dependencies in the Python environment that "
    "runs the app, then restart it."
)


@dataclass(frozen=True, slots=True)
class EnvironmentReport:
    """Immutable engine version, supported impersonation targets, and warnings."""

    yt_dlp_version: str
    impersonation_targets: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def _impersonation_targets(engine: yt_dlp.YoutubeDL) -> tuple[str, ...]:
    # Verified in yt-dlp 2026.08.19. Upstream marks a public API as a future TODO;
    # confine this private dependency here so API changes have one repair point.
    available = engine._get_available_impersonate_targets()
    return tuple(sorted({str(target) for target, _handler in available}))


def check_environment() -> EnvironmentReport:
    """Check runtime impersonation capabilities without contacting a website.

    Package presence alone does not establish that yt-dlp loaded a usable native
    request handler. This check asks the engine for its actual supported targets.
    The full FFmpeg and JavaScript report is provided by core/environment.py.

    Returns:
        Engine version, sorted unique targets, and actionable nonfatal warnings.
        Failure to inspect capabilities also produces a warning and a redacted log.
    """
    try:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "cachedir": False,
                "logger": EngineLogger(_LOGGER),
            },
            auto_init=False,
        ) as engine:
            targets = _impersonation_targets(engine)
    except Exception as error:
        log_exception(_LOGGER, "Browser impersonation environment check failed.", error)
        return EnvironmentReport(
            YT_DLP_VERSION,
            (),
            (f"Browser impersonation availability could not be checked. {_INSTALL_INSTRUCTION}",),
        )
    warnings = (
        ()
        if targets
        else (
            "No browser impersonation target is available. Some sites require curl-cffi. "
            + _INSTALL_INSTRUCTION,
        )
    )
    return EnvironmentReport(YT_DLP_VERSION, targets, warnings)
