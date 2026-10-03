"""Smoke checks for the installed src-layout package."""

from importlib import import_module
from importlib.metadata import metadata, version

import pytest
from packaging.requirements import Requirement
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


def test_runtime_impersonation_dependencies_match_supported_engine_extra() -> None:
    requirements = {
        requirement.name: requirement
        for text in metadata("mediagrab").get_all("Requires-Dist", [])
        if (requirement := Requirement(text)).marker is None
    }
    assert {"default", "curl-cffi"} <= requirements["yt-dlp"].extras
    declared = requirements["curl-cffi"].specifier
    assert "0.16.0" in declared and version("curl-cffi") in declared
    assert "0.15.0" not in declared and "0.17.0" not in declared
    upstream = next(
        requirement
        for text in metadata("yt-dlp").get_all("Requires-Dist", [])
        if (requirement := Requirement(text)).name == "curl-cffi"
        and requirement.marker is not None
        and requirement.marker.evaluate({"extra": "curl-cffi"})
    )
    assert "curl-cffi" in metadata("yt-dlp").get_all("Provides-Extra", [])
    assert version("curl-cffi") in upstream.specifier
