"""Shared test configuration; network access requires explicit opt-in."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the opt-in flag for network integration tests.

    Args:
        parser: Pytest command-line option parser.
    """
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run network tests that download media and require FFmpeg.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip marked network tests unless explicitly enabled.

    Args:
        config: Active pytest configuration.
        items: Collected test cases.
    """
    if config.getoption("--run-network"):
        return
    skip_network = pytest.mark.skip(reason="Network tests require --run-network.")
    for item in items:
        if item.get_closest_marker("network") is not None:
            item.add_marker(skip_network)


@pytest.fixture(autouse=True)
def mock_desktop_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Desktop tests never probe the user's native tool installations."""
    from mediagrab.core.environment import EnvironmentItem, EnvironmentResult, Severity
    from mediagrab.desktop import engine_workers

    monkeypatch.setattr(
        engine_workers,
        "inspect_environment",
        lambda _cancel: EnvironmentResult((EnvironmentItem("yt-dlp", Severity.OK, "fixture"),)),
    )
