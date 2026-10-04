# Local Windows packaging

Binaries are not currently distributed. These instructions produce a local build.
Run commands from the repository root.


Build on Windows x64 using Python 3.14. Internet access is required for pinned
upstream binaries and their published checksums. A complete local bundle needs no Python, system FFmpeg or
system Deno installation on the target machine. Windows 10/11 x64
is the target; the local frozen verification was performed on Windows 11.

```powershell
.\.venv\Scripts\python.exe -m pip install --editable ".[dev,build]"
.\scripts\build_windows.ps1
# With another installed Python 3.14 environment:
# .\scripts\build_windows.ps1 -Python python
```

The committed `mediagrab.spec` builds **MediaGrab**, onedir/windowed, with no UPX.
The version comes from `pyproject.toml` through installed distribution metadata;
the build refuses stale metadata. Full QSS/icon resources and metadata are copied.
Runtime collection includes yt-dlp extractors/plugin support, EJS scripts/data,
curl-cffi native libraries, certifi's CA bundle and Qt platforms/styles/imageformats.
Installed namespace plugins are collected as real files for yt-dlp's finder;
the default environment has no third-party extractor plugins.

Downloads are pinned in `scripts/tools.json`: FFmpeg 9.0.2 Gyan essentials x64
(GPLv3, required for existing libx264 compatibility conversion), and official
Deno 2.9.7 x64 (MIT). The scripts compare the downloaded published checksum with
the committed digest, verify the archive, then extract into ignored
`vendor/packaging/`. Binaries are never committed. Deno adds 97,462,048 bytes
uncompressed (42,630,221-byte upstream zip). FFmpeg and ffprobe add 210,644,992
bytes uncompressed. Bundling Deno avoids a separate YouTube runtime install.
FFmpeg itself publishes source; Gyan's Windows supplier is linked from the
[official FFmpeg download page](https://ffmpeg.org/download.html).

The build runs self-check and GUI smoke before creating:

```text
dist/MediaGrab/MediaGrab.exe
dist/MediaGrab/ffmpeg.exe
dist/MediaGrab/ffprobe.exe
dist/MediaGrab/deno.exe
dist/MediaGrab/_internal/...
dist/MediaGrab-0.1.0-windows-x64.zip
dist/MediaGrab-0.1.0-windows-x64.zip.sha256
```

Extract the **entire zip** into an ordinary writable folder. Keep `_internal`,
the three tool executables, LICENSE and THIRD_PARTY_NOTICES.md with MediaGrab.exe.
Do not move only the executable. Launch:

The bundled README's relative documentation links refer to the source repository;
the build does not copy the docs directory into the application folder.

```powershell
.\dist\MediaGrab\MediaGrab.exe
```

For an offline check without creating a GUI or changing disclaimer acceptance:

```powershell
$appExe = (Resolve-Path .\dist\MediaGrab\MediaGrab.exe).Path
$reportPath = Join-Path $PWD 'build\self-check.json'
$check = Start-Process -FilePath $appExe -ArgumentList @('--self-check', '--report', "`"$reportPath`"") -WindowStyle Hidden -PassThru -Wait
$check.ExitCode # 0 means all required capabilities passed; 1 means failure
Get-Content -LiteralPath $reportPath
```

The report includes versions, local paths, extractor count, native impersonation
targets, certificate/EJS resources and offline EJS evaluation by bundled Deno.
Self-check requires bundled FFmpeg, ffprobe and Deno beside the exe. It explicitly
uses a minimal PATH internally; missing optional Node/Bun/QuickJS is acceptable.
Windowed builds have no normal console; use `--report` for dependable output.
Redirected stdout is also recovered and receives the JSON through logging.
Reports contain local paths and are intended for local inspection.

Repeat both deployment checks from a clean temporary copy:

```powershell
.\scripts\smoke_frozen.ps1
# Or check a separately extracted distribution:
.\scripts\smoke_frozen.ps1 -AppDirectory 'C:\Temp\MediaGrab-clean'
```

The script copies the complete folder to a unique temp directory, starts from an
unrelated working directory, removes inherited offscreen Qt selection, uses a
minimal PATH (Windows/System32 and Windows), and waits for clean process exit.
`--smoke-test` shows the real main window, Environment, disclaimer and About,
checks image plugins and both themes, awaits the real offline environment worker,
then closes cooperatively. Smoke uses temporary INI settings and never accepts
the responsible-use disclaimer on the user's behalf. It performs no live download.

### Tagged release workflow

The existing CI is retained. `.github/workflows/release.yml` runs only on `v*`
tags and requires the tag to equal the project version (currently `v0.1.0`). It
uses Windows/Python 3.14, installs, checks dependencies, runs lint/format and
sequential offline coverage, builds, smokes and creates a zip/SHA-256 pair.
Actions are pinned to verified commit hashes. Only the separate release job gets
`contents: write`; it uploads the verified artifacts using GitHub CLI.

Before publishing this GPL static FFmpeg bundle, the distributor must prepare a
reviewed **complete corresponding-source zip** for this exact FFmpeg build,
including linked dependency sources and build scripts, and source for the
distributed GPL/LGPL components. The workflow requires repository variables
`MEDIAGRAB_CORRESPONDING_SOURCE_URL` (HTTPS) and
`MEDIAGRAB_CORRESPONDING_SOURCE_SHA256`; it verifies and publishes that archive
and its checksum alongside the app. Without these variables the workflow fails
before publication. Hash verification does not establish source completeness;
the distributor must review that separately. Binaries are not currently distributed.
A link to FFmpeg alone is insufficient. Full GPLv3, Deno MIT
and Qt LGPLv3 text is in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md); wheel notices, Python licence and
tool provenance are under `_internal/licenses`. No tag or release was created
during local Phase 6 work.

### Phase 6 manual checklist

1. Run the build command above; confirm both smoke modes pass and a zip/hash exist.
2. Extract the entire zip into a fresh folder with spaces in its path, outside
   the repository. Run MediaGrab.exe from there and from a different working folder.
3. Verify first-run responsible-use handling, About/version, both themes and icons.
   Existing accepted QSettings remain shared with source launches.
4. Open Settings > Engine/Environment: FFmpeg 9.0.2, ffprobe 9.0.2 and Deno 2.9.7
   must point beside the copied exe; EJS and impersonation targets must be present.
   Confirm the updater says to update MediaGrab for a newer engine.
5. Run `smoke_frozen.ps1 -AppDirectory <extracted-folder>` for the clean temp copy
   and automated minimal-PATH check. For an interactive check, use a throwaway shell:

   ```powershell
   $cleanExe = 'C:\Temp\MediaGrab-clean\MediaGrab.exe'
   $savedPath = $env:PATH
   try {
       $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
       Start-Process -FilePath $cleanExe -Wait
   } finally { $env:PATH = $savedPath }
   ```

6. Verify diagnostics, logs and normal close. Optional permitted live check:
   paste `https://download.blender.org/peach/trailer/trailer_iphone.m4v`, select
   Best, download MP4 and MP3, and inspect playback. This live frozen download is
   optional and was not part of the offline gate.
7. Verify the zip's SHA-256 before using or distributing it, as described below.

