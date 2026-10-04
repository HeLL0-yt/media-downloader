# -*- mode: python ; coding: utf-8 -*-
"""Windows x64 onedir build; package data and native tools remain replaceable."""

import importlib.util
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)
from PyInstaller.utils.hooks.qt import pyside6_library_info

root = Path(SPECPATH)
# Set PATH inside the build process as well: launch wrappers can restore their
# developer PATH after the PowerShell script sets it. Qt's ICU imports must use
# Windows' own C API, never an unrelated Poppler/Conda ICU with renamed exports.
windows = Path(os.environ["SystemRoot"])
os.environ["PATH"] = os.pathsep.join((str(windows / "System32"), str(windows)))
datas = collect_data_files("mediagrab")
hiddenimports = collect_submodules(
    "yt_dlp", filter=lambda name: not name.startswith("yt_dlp.__pyinstaller")
) + collect_submodules("yt_dlp_ejs")
hiddenimports += collect_submodules("curl_cffi", filter=lambda name: name != "curl_cffi.__main__")
binaries = collect_dynamic_libs("curl_cffi")
datas += collect_data_files("curl_cffi")
datas += collect_data_files("yt_dlp") + collect_data_files("yt_dlp_ejs")
datas += collect_data_files("certifi")
for package in ("mediagrab", "yt-dlp", "yt-dlp-ejs", "curl-cffi", "certifi", "PySide6"):
    datas += copy_metadata(package)

# yt-dlp's namespace plugin finder scans real directories, not PYZ members.
for namespace in ("yt_dlp_plugins", "ytdlp_plugins"):
    if importlib.util.find_spec(namespace) is not None:
        hiddenimports += collect_submodules(namespace)
        datas += collect_data_files(namespace, include_py_files=True)

# Keep PyInstaller's Qt dependency analysis and runtime hook; include all required
# plugin families explicitly. Do not collect unrelated Qt WebEngine/QML modules.
for family in ("platforms", "styles", "imageformats"):
    binaries += pyside6_library_info.collect_plugins(family)
hiddenimports += ["PySide6.QtSvg"]
datas += [(str(root / "build" / "licenses"), "licenses")]

a = Analysis(
    [str(root / "scripts" / "frozen_entry.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "pytest", "tkinter"],
    noarchive=False,
)
allowed_binary_roots = (Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), windows.resolve())
for destination, source, kind in a.binaries:
    if not any(Path(source).resolve().is_relative_to(base) for base in allowed_binary_roots):
        raise RuntimeError(f"Refusing a native dependency from outside Python/packages/Windows: {source}")
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="MediaGrab",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "src" / "mediagrab" / "desktop" / "resources" / "mediagrab.ico"),
    version=str(root / "build" / "version-info.txt"),
    contents_directory="_internal",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MediaGrab")
