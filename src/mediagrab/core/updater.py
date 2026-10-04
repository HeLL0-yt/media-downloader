"""Confirmed development-environment updates from official HTTPS metadata."""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from threading import Event
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from mediagrab.core.env_check import YT_DLP_VERSION
from mediagrab.core.errors import DownloadCancelledError
from mediagrab.core.logging_utils import redact_message
from mediagrab.core.process import run_process

_RELEASE_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
_MAX_METADATA = 2 * 1024 * 1024
_MAX_WHEEL = 32 * 1024 * 1024


class UpdateError(Exception):
    """Safe application-owned update failure."""


@dataclass(frozen=True, slots=True)
class EngineRelease:
    """Exact release and verified official wheel identity."""

    version: str
    wheel_url: str
    sha256: str


class _HttpsRedirects(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: object, code: int, msg: str, headers: object, newurl: str
    ) -> Request | None:
        if urlsplit(newurl).scheme != "https":
            raise UpdateError("An insecure update redirect was refused.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_https(url: str, limit: int, cancel: Event) -> bytes:
    if cancel.is_set():
        raise DownloadCancelledError()
    if urlsplit(url).scheme != "https":
        raise UpdateError("Updates require HTTPS.")
    request = Request(url, headers={"User-Agent": "MediaGrab/0.1", "Accept": "application/json"})  # noqa: S310 -- HTTPS checked
    opener = build_opener(HTTPSHandler(), _HttpsRedirects())
    try:
        with opener.open(request, timeout=5) as response:
            data = bytearray()
            deadline = time.monotonic() + 30
            while True:
                if cancel.is_set():
                    raise DownloadCancelledError()
                if time.monotonic() >= deadline:
                    raise UpdateError("Update request timed out. Retry later.")
                chunk = response.read(64 * 1024)
                if not chunk:
                    return bytes(data)
                data.extend(chunk)
                if len(data) > limit:
                    raise UpdateError("Update response exceeded its size limit.")
    except OSError as error:
        raise UpdateError("Update service unavailable. Check your connection and retry.") from error


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def check_latest(cancel_event: Event | None = None) -> EngineRelease:
    """Read official release/PyPI metadata without executing or installing code."""
    cancel = cancel_event if cancel_event is not None else Event()
    try:
        release = json.loads(_read_https(_RELEASE_URL, _MAX_METADATA, cancel))
        if not isinstance(release, dict):
            raise UpdateError("Invalid update metadata. Retry later.")
        if release.get("draft") or release.get("prerelease"):
            raise UpdateError("Only stable official releases are supported.")
        tag = release["tag_name"]
        if not isinstance(tag, str) or not re.fullmatch(r"2026\.\d{1,2}\.\d{1,2}", tag):
            raise UpdateError("This engine release is outside the supported 2026 range.")
        version = ".".join(str(part) for part in _version_tuple(tag))
        metadata = json.loads(
            _read_https(f"https://pypi.org/pypi/yt-dlp/{version}/json", _MAX_METADATA, cancel)
        )
        for file in metadata["urls"]:
            if file["packagetype"] != "bdist_wheel" or not file["filename"].endswith(
                "-py3-none-any.whl"
            ):
                continue
            url, digest = file["url"], file["digests"]["sha256"]
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or parsed.hostname != "files.pythonhosted.org"
                or parsed.username
                or parsed.password
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
            ):
                raise UpdateError("Invalid official wheel identity; update refused.")
            return EngineRelease(version, url, digest)
        raise UpdateError("The official release has no supported wheel yet. Retry later.")
    except (ValueError, KeyError, TypeError) as error:
        raise UpdateError("Invalid update metadata. Retry later.") from error


def is_newer(release: EngineRelease) -> bool:
    """Compare calendar version components without lexical ordering errors."""
    return _version_tuple(release.version) > _version_tuple(YT_DLP_VERSION)


def update_engine(
    release: EngineRelease,
    *,
    confirmed: bool,
    downloads_active: bool,
    cancel_event: Event | None = None,
) -> str:
    """Verify the official wheel and install through this interpreter's pip.

    No shell is used. Pip re-verifies the hash on its download. Frozen and system
    installations are refused; restarting is required to load the new engine.
    """
    if not confirmed:
        raise UpdateError("Engine update requires explicit user confirmation.")
    if downloads_active:
        raise UpdateError("Finish or cancel all downloads before updating the engine.")
    if getattr(sys, "frozen", False):
        raise UpdateError("Update MediaGrab to get a newer engine. Bundled engines cannot use pip.")
    if sys.prefix == sys.base_prefix:
        raise UpdateError("Use a virtual environment to update the engine safely.")
    # Do not trust a stale or caller-created download URL/hash. Re-read official metadata.
    cancel = cancel_event if cancel_event is not None else Event()
    current = check_latest(cancel)
    if current != release or not is_newer(current):
        raise UpdateError("Release metadata changed or no newer engine exists. Check again.")
    wheel = _read_https(current.wheel_url, _MAX_WHEEL, cancel)
    if hashlib.sha256(wheel).hexdigest() != current.sha256:
        raise UpdateError("Engine checksum mismatch. Nothing was installed.")
    requirement = f"yt-dlp[default,curl-cffi] @ {current.wheel_url}#sha256={current.sha256}"
    try:
        result = run_process(
            [
                sys.executable,
                "-m",
                "pip",
                "--isolated",
                "--disable-pip-version-check",
                "install",
                "--upgrade",
                "--only-binary=:all:",
                "--index-url",
                "https://pypi.org/simple",
                "--timeout",
                "5",
                "--retries",
                "1",
                "curl-cffi>=0.16.0,<0.17",
                requirement,
            ],
            timeout=180,
            cancel_event=cancel,
            env={
                **{
                    key: value
                    for key, value in os.environ.items()
                    if not key.upper().startswith("PIP_")
                },
                "PIP_CONFIG_FILE": os.devnull,
            },
        )
    except OSError as error:
        raise UpdateError("Pip could not start. Check the virtual environment.") from error
    except subprocess.SubprocessError as error:
        raise UpdateError(
            "Pip update failed or timed out. Run pip check; retry or repair the venv."
        ) from error
    return redact_message(result.stdout + result.stderr)
