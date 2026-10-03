"""Offline capability checks cover absent, working, and broken engine handlers."""

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, Mock

import pytest
from yt_dlp.networking.impersonate import ImpersonateTarget

from mediagrab.core import env_check


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    engine = MagicMock()
    engine.__enter__.return_value = engine
    engine._get_available_impersonate_targets.return_value = []
    monkeypatch.setattr(env_check.yt_dlp, "YoutubeDL", Mock(return_value=engine))
    return engine


def test_missing_targets_produce_actionable_warning(engine: MagicMock) -> None:
    report = env_check.check_environment()
    assert report.yt_dlp_version == env_check.YT_DLP_VERSION
    assert report.impersonation_targets == ()
    assert len(report.warnings) == 1
    assert "No browser impersonation target" in report.warnings[0]
    assert "curl-cffi" in report.warnings[0]
    assert "Python environment" in report.warnings[0]
    engine.__exit__.assert_called_once()
    engine.urlopen.assert_not_called()


def test_available_targets_are_sorted_and_unique(engine: MagicMock) -> None:
    chrome = ImpersonateTarget("chrome", "131", "windows", "10")
    safari = ImpersonateTarget("safari", "18", "macos", "15")
    engine._get_available_impersonate_targets.return_value = [
        (safari, "curl_cffi"),
        (chrome, "curl_cffi"),
        (chrome, "another handler"),
    ]
    report = env_check.check_environment()
    assert report.impersonation_targets == (str(chrome), str(safari))
    assert not report.warnings
    with pytest.raises(FrozenInstanceError):
        report.warnings = ()  # type: ignore[misc]


@pytest.mark.parametrize("failure", [ImportError("DLL unavailable"), AttributeError("API changed")])
def test_failed_checks_warn_without_aborting(
    engine: MagicMock,
    failure: Exception,
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine._get_available_impersonate_targets.side_effect = failure
    report = env_check.check_environment()
    assert report.impersonation_targets == ()
    assert "could not be checked" in report.warnings[0]
    assert "environment check failed" in caplog.text


def test_constructor_failure_is_also_nonfatal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        env_check.yt_dlp, "YoutubeDL", Mock(side_effect=OSError("initialization failed"))
    )
    assert env_check.check_environment().warnings


def test_real_installed_engine_has_targets_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    network = Mock(side_effect=AssertionError("Environment checks must not contact websites"))
    monkeypatch.setattr(env_check.yt_dlp.YoutubeDL, "urlopen", network)
    report = env_check.check_environment()
    assert report.impersonation_targets
    assert not report.warnings
    network.assert_not_called()
