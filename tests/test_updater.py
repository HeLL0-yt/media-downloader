"""Updater uses mocked HTTPS/pip and rejects unsafe or unconfirmed operations."""

import hashlib
import json
import os
import subprocess
from io import BytesIO
from threading import Event
from unittest.mock import Mock
from urllib.request import Request

import pytest

from mediagrab.core import updater
from mediagrab.core.errors import DownloadCancelledError

WHEEL = b"offline wheel fixture"
RELEASE = updater.EngineRelease(
    "2026.12.1", "https://files.pythonhosted.org/engine.whl", hashlib.sha256(WHEEL).hexdigest()
)


@pytest.fixture
def pip_mock(monkeypatch: pytest.MonkeyPatch) -> Mock:
    monkeypatch.setattr(updater.sys, "prefix", "fixture-venv")
    monkeypatch.setattr(updater.sys, "base_prefix", "fixture-python")
    monkeypatch.setattr(updater, "check_latest", lambda _cancel: RELEASE)
    monkeypatch.setattr(updater, "_read_https", lambda *_args: WHEEL)
    runner = Mock(
        return_value=subprocess.CompletedProcess([], 0, "installed https://secret/path", "")
    )
    monkeypatch.setattr(updater, "run_process", runner)
    return runner


def test_success_verifies_hash_and_same_environment_pip(
    pip_mock: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PIP_EXTRA_INDEX_URL", "http://untrusted")
    result = updater.update_engine(RELEASE, confirmed=True, downloads_active=False)
    assert "secret" not in result
    args = pip_mock.call_args.args[0]
    assert args[:3] == [updater.sys.executable, "-m", "pip"]
    assert "--isolated" in args and "--only-binary=:all:" in args
    assert "#sha256=" + RELEASE.sha256 in args[-1]
    assert args[args.index("--index-url") + 1] == "https://pypi.org/simple"
    assert pip_mock.call_args.kwargs["env"]["PIP_CONFIG_FILE"] == os.devnull
    assert "PIP_EXTRA_INDEX_URL" not in pip_mock.call_args.kwargs["env"]
    assert isinstance(pip_mock.call_args.kwargs["cancel_event"], Event)


@pytest.mark.parametrize("confirmed,active", [(False, False), (True, True)])
def test_unconfirmed_or_active_never_runs_pip(
    pip_mock: Mock, confirmed: bool, active: bool
) -> None:
    with pytest.raises(updater.UpdateError):
        updater.update_engine(RELEASE, confirmed=confirmed, downloads_active=active)
    pip_mock.assert_not_called()


@pytest.mark.parametrize("frozen", [False, True])
def test_unsupported_installations_are_refused(
    pip_mock: Mock, monkeypatch: pytest.MonkeyPatch, frozen: bool
) -> None:
    if frozen:
        monkeypatch.setattr(updater.sys, "frozen", True, raising=False)
    else:
        monkeypatch.setattr(updater.sys, "prefix", updater.sys.base_prefix)
    with pytest.raises(updater.UpdateError):
        updater.update_engine(RELEASE, confirmed=True, downloads_active=False)
    pip_mock.assert_not_called()


@pytest.mark.parametrize("mode", ["changed", "same-version", "checksum"])
def test_release_identity_failures_never_run_pip(
    pip_mock: Mock, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    if mode == "changed":
        monkeypatch.setattr(
            updater,
            "check_latest",
            lambda _cancel: updater.EngineRelease("2026.12.2", RELEASE.wheel_url, RELEASE.sha256),
        )
    elif mode == "same-version":
        monkeypatch.setattr(updater, "is_newer", lambda _release: False)
    else:
        monkeypatch.setattr(updater, "_read_https", lambda *_args: b"tampered")
    with pytest.raises(updater.UpdateError):
        updater.update_engine(RELEASE, confirmed=True, downloads_active=False)
    pip_mock.assert_not_called()


@pytest.mark.parametrize(
    "error", [OSError(), subprocess.TimeoutExpired([], 180), DownloadCancelledError()]
)
def test_pip_errors_and_cancellation(pip_mock: Mock, error: Exception) -> None:
    pip_mock.side_effect = error
    with pytest.raises(
        DownloadCancelledError if isinstance(error, DownloadCancelledError) else updater.UpdateError
    ):
        updater.update_engine(RELEASE, confirmed=True, downloads_active=False)


def metadata(
    monkeypatch: pytest.MonkeyPatch,
    *,
    url: str = RELEASE.wheel_url,
    digest: str = RELEASE.sha256,
    tag: str = "2026.12.01",
    wheel: bool = True,
) -> None:
    responses = [
        json.dumps({"tag_name": tag}).encode(),
        json.dumps(
            {
                "urls": [
                    {
                        "packagetype": "bdist_wheel" if wheel else "sdist",
                        "filename": "yt_dlp-py3-none-any.whl",
                        "url": url,
                        "digests": {"sha256": digest},
                    }
                ]
            }
        ).encode(),
    ]
    monkeypatch.setattr(updater, "_read_https", Mock(side_effect=responses))


def test_release_metadata_and_numeric_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata(monkeypatch)
    assert updater.check_latest() == RELEASE
    assert updater.is_newer(RELEASE)
    assert not updater.is_newer(
        updater.EngineRelease("2026.1.1", RELEASE.wheel_url, RELEASE.sha256)
    )


@pytest.mark.parametrize(
    "values",
    [
        {"tag": "2027.01.01"},
        {"tag": "invalid"},
        {"wheel": False},
        {"url": "http://files.pythonhosted.org/x"},
        {"url": "https://evil.example/x"},
        {"url": "https://user:password@files.pythonhosted.org/x"},
        {"digest": "invalid"},
    ],
)
def test_invalid_metadata(monkeypatch: pytest.MonkeyPatch, values: dict[str, object]) -> None:
    metadata(monkeypatch, **values)
    with pytest.raises(updater.UpdateError):
        updater.check_latest()


@pytest.mark.parametrize("data", [b"not json", b"{}", b"[]"])
def test_malformed_release_metadata(monkeypatch: pytest.MonkeyPatch, data: bytes) -> None:
    monkeypatch.setattr(updater, "_read_https", lambda *_args: data)
    with pytest.raises(updater.UpdateError):
        updater.check_latest()


def test_https_stream_bounds_offline_cancel_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = Mock()
    monkeypatch.setattr(updater, "build_opener", lambda *_args: opener)
    opener.open.return_value = BytesIO(b"fixture")
    assert updater._read_https("https://pypi.org/x", 10, Event()) == b"fixture"
    assert opener.open.call_args.kwargs["timeout"] == 5
    with pytest.raises(updater.UpdateError, match="HTTPS"):
        updater._read_https("http://pypi.org/x", 10, Event())
    opener.open.return_value = BytesIO(b"oversized")
    with pytest.raises(updater.UpdateError, match="size limit"):
        updater._read_https("https://pypi.org/x", 1, Event())
    opener.open.return_value = BytesIO(b"fixture")
    cancel = Event()
    cancel.set()
    with pytest.raises(DownloadCancelledError):
        updater._read_https("https://pypi.org/x", 10, cancel)
    opener.open.side_effect = OSError("raw signed URL")
    with pytest.raises(updater.UpdateError, match="unavailable"):
        updater._read_https("https://pypi.org/x", 10, Event())
    opener.open.side_effect = None
    opener.open.return_value = BytesIO(b"fixture")
    monkeypatch.setattr(updater.time, "monotonic", Mock(side_effect=[0, 31]))
    with pytest.raises(updater.UpdateError, match="timed out"):
        updater._read_https("https://pypi.org/x", 10, Event())


def test_redirect_downgrade_is_refused() -> None:
    handler = updater._HttpsRedirects()
    request = Request("https://pypi.org/x")
    with pytest.raises(updater.UpdateError):
        handler.redirect_request(request, None, 302, "Found", {}, "http://pypi.org/x")
    redirected = handler.redirect_request(request, None, 302, "Found", {}, "https://pypi.org/y")
    assert redirected.full_url == "https://pypi.org/y"
