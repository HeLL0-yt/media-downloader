"""Shared test configuration; network access requires explicit opt-in."""

import pytest


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
