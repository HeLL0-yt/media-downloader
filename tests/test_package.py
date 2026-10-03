"""Smoke checks for the installed src-layout package."""

from importlib import import_module
from importlib.metadata import metadata, version

import pytest
from packaging.specifiers import SpecifierSet

from mediagrab import __version__


@pytest.mark.parametrize("name", ["mediagrab", "mediagrab.core", "mediagrab.desktop"])
def test_packages_are_importable(name: str) -> None:
    module = import_module(name)

    assert module.__name__ == name
    assert module.__file__ is not None


def test_distribution_metadata_matches_package() -> None:
    assert version("mediagrab") == __version__
    supported = SpecifierSet(metadata("mediagrab")["Requires-Python"])
    assert "3.14.0" in supported
    assert "3.13.9" not in supported
    assert "3.15.0" not in supported
