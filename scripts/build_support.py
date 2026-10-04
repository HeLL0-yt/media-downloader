"""Prepare Windows version information and retain dependency redistribution notices."""

import importlib.metadata
import json
import logging
import shutil
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Generate build-only metadata from the installed pyproject version."""
    config = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = importlib.metadata.version("mediagrab")
    if version != config["project"]["version"]:
        raise ValueError("Reinstall the project: installed metadata differs from pyproject.toml.")
    if sys.version_info[:2] != (3, 14) or sys.maxsize <= 2**32:
        raise ValueError("Build with 64-bit Python 3.14.")
    folder = _ROOT / "build"
    folder.mkdir(exist_ok=True)
    numbers = tuple(int(part) for part in version.split("."))
    numbers = (*numbers, *([0] * (4 - len(numbers))))
    information = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers, fileType=1),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("FileDescription", "MediaGrab"),
                            StringStruct("FileVersion", version),
                            StringStruct("ProductName", "MediaGrab"),
                            StringStruct("ProductVersion", version),
                            StringStruct("OriginalFilename", "MediaGrab.exe"),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
    (folder / "version-info.txt").write_text(str(information), encoding="utf-8")
    (folder / "version.txt").write_text(version, encoding="ascii")
    licenses = folder / "licenses"
    licenses.mkdir(exist_ok=True)
    # Preserve wheel-supplied full notices, including EJS's MIT/ISC dependency text.
    # These text files are not executable and do not enter the source repository.
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata["Name"]
        for file in distribution.files or ():
            if not any(token in str(file).lower() for token in ("license", "copying", "notice")):
                continue
            if file.suffix.lower() not in {"", ".txt", ".md", ".rst"}:
                continue
            source = Path(distribution.locate_file(file))
            if source.is_file():
                target = licenses / name / file.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python-LICENSE.txt")
    for name in ("ffmpeg", "deno"):
        vendor = _ROOT / "vendor" / "packaging" / name
        manifest = json.loads((vendor / "verified.json").read_text(encoding="utf-8"))
        shutil.copy2(vendor / "verified.json", licenses / f"{name}-provenance.json")
        if (
            manifest["version"]
            != json.loads((_ROOT / "scripts/tools.json").read_text())[name]["version"]
        ):
            raise ValueError("Tool manifest version differs from the pinned build configuration.")
        if name == "ffmpeg":
            for source in (vendor / "upstream").rglob("*"):
                if source.is_file() and source.suffix.lower() in {".txt", ".html"}:
                    target = licenses / "ffmpeg" / source.relative_to(vendor / "upstream")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    logging.info("Prepared MediaGrab %s version information and licences.", version)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
