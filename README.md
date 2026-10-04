# MediaGrab

**Source-only: binaries are not currently distributed.** The maintainer will not
publish a binary Release for now because the selected Gyan FFmpeg build is
GPLv3 (libx264). Local build instructions remain available.

MediaGrab is a Python 3.14 desktop application being built for Windows 10/11.
Its download engine uses yt-dlp as a library, FFmpeg for media processing,
and PySide6 for the interface.

**Current status: Phases 0–6 implemented. Phase 4 Windows platform checks passed,
verified manually by the user on 2026-10-04, not by automated tests. Phase 5's
offline automated gate passed. On 2026-10-04 the user manually verified the
first-run disclaimer, About, Engine/Environment panel, diagnostics, logs and
normal MP4/MP3 downloads on Windows. The live updater and missing-Deno/FFmpeg
simulation were not run; the remaining manual instructions are in docs/NOTES.md.
Phase 6 adds a locally verified Windows onedir build and tagged release workflow.
Phase 7 has not started.**

## Existing features

- Real desktop and CLI metadata extraction and MP4/MP3 downloads through yt-dlp.
- Metadata card with title, uploader, duration and asynchronous optional thumbnail.
  Video quality choices come from reported heights; Best handles unknown heights.
- Queue with 1–4 parallel downloads (default 2), per-task progress/speed/ETA,
  cancel, retry, remove and open folder.
- QSettings preferences for default folder, mode/video quality/audio bitrate,
  parallelism, H.264/AAC compatibility, MP3 artwork, opt-in browser cookies and
  dark/light theme. Queued requests retain the settings used when added.
- Safe typed errors with retry guidance and rotating redacted local diagnostic logs.
- Asynchronous startup environment checks and Settings > Engine/Environment panel:
  engine/EJS versions, FFmpeg/ffprobe versions/locations, JavaScript runtimes and
  real browser impersonation targets. Warnings do not disable downloads.
- Confirmed, cancellable venv engine updater with official HTTPS metadata and
  SHA-256 wheel verification, plus Open logs folder and Copy diagnostics.
- First-run responsible-use acceptance, persisted in QSettings; Help exposes
  About (versions, MIT license, repository) and the disclaimer again.
- Clipboard/URL drag-drop input and cooperative shutdown that waits for workers.
- Windows x64 portable onedir packaging with bundled FFmpeg/ffprobe and Deno,
  package metadata, EJS data, native impersonation/TLS support and Qt plugins.
- Non-GUI deployment self-check, clean-PATH GUI smoke script, zip/SHA-256 output
  and a tag-triggered release workflow. Builds are unsigned.

## Desktop launch and usage

```powershell
python -m mediagrab.desktop.app
# Or use the installed project environment:
.\.venv\Scripts\python.exe -m mediagrab.desktop.app
```

Paste a URL and select Analyze. Choose Video (MP4) or MP3, quality and output
folder. Download adds the selection and starts the queue; Add to queue stages it
until the queue is started, or joins an already running queue. Use each row's
buttons or context menu for Cancel, Retry, Open folder and Remove. Active rows
must finish cancellation before retry/removal. Settings opens the defaults dialog;
saved preferences apply immediately and persist across launches. Browser cookies
are disabled by default.

Startup checks run on a worker. Open Settings > Engine/Environment for repair
commands, Refresh environment, Check latest release, Update engine, logs and
redacted diagnostics. The release check runs only when requested. Updates require
a virtual environment, explicit confirmation and no active downloads/analysis.
Queued downloads pause during updating; restart after any install attempt before
using the engine again. Check/repair the venv after a cancelled or failed pip run.
System Python and frozen-build updates are refused. In a packaged app, update
MediaGrab to get a newer engine; no pip installation changes bundled files.

The desktop now uses real core workers. Simulation exists only in test helpers.
Progress is per transfer/stream; processing is distinct from success. On close,
the window shows Stopping workers and remains open until all workers exit.
Upstream extraction/FFmpeg operations finish at cooperative cancellation
boundaries; immediate cancellation is not guaranteed. No running thread is
forcibly terminated, and worker ownership is retained throughout shutdown.

## Development setup

Use 64-bit CPython 3.14. Run these commands from the repository root in PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
.\.venv\Scripts\python.exe -m pip check
```

The project uses a `src/` layout. Install it before running tests; changing
`PYTHONPATH` is unnecessary. FFmpeg and a JavaScript runtime are external binaries,
not Python packages. Get both FFmpeg executables from a Windows build linked on
the [FFmpeg download page](https://ffmpeg.org/download.html), then add their shared
folder to PATH. Source launches use external tools; the Windows package bundles
both FFmpeg executables and Deno. Install Deno (recommended) for source YouTube use:

```powershell
winget install DenoLand.Deno
winget install Gyan.FFmpeg
```

Restart the shell and app after PATH changes. The installed yt-dlp 2026.08.19
supports Deno ≥2.3.0, Node ≥22, Bun ≥1.2.11 and QuickJS ≥2023-12-09 (or QuickJS-ng).
MediaGrab enables discovered supported runtime names explicitly with executable
paths in `js_runtimes`; it searches Python's scripts directory and absolute PATH
folders in source mode. Frozen discovery prefers the executable folder, then
`_internal`, then absolute PATH folders; it does not consult Python scripts.
EJS comes from the engine's default extra; remote EJS fetching is disabled.
The startup check applies version minimums from the installed engine.

## Windows build and portable launch

Build on Windows x64 using Python 3.14. Internet access is required for pinned
upstream binaries and their published checksums. No Python, system FFmpeg or
system Deno installation is required on the target machine. Windows 10/11 x64
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

```powershell
.\dist\MediaGrab\MediaGrab.exe
```

For an offline check without creating a GUI or changing disclaimer acceptance:

```powershell
$appExe = (Resolve-Path .\dist\MediaGrab\MediaGrab.exe).Path
$reportPath = Join-Path $PWD 'build\self-check.json'
$check = Start-Process -FilePath $appExe -ArgumentList @('--self-check', '--report', "`"$reportPath`"") -PassThru -Wait
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
before publication. A link to FFmpeg alone is insufficient. Full GPLv3, Deno MIT
and Qt LGPLv3 text is in THIRD_PARTY_NOTICES.md; wheel notices, Python licence and
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

## Manual downloads

Use only media you have permission to download. These examples use Blender's
Creative Commons trailer and save into the local `downloads/` folder:

```powershell
.\.venv\Scripts\python.exe -m mediagrab.core.cli "https://download.blender.org/peach/trailer/trailer_iphone.m4v"
.\.venv\Scripts\python.exe -m mediagrab.core.cli "https://download.blender.org/peach/trailer/trailer_iphone.m4v" --audio --bitrate 192
```

The manual verification interface also supports:

```powershell
.\.venv\Scripts\python.exe -m mediagrab.core.cli "<media-url>" --height 1080 --output-dir ".\downloads"
.\.venv\Scripts\python.exe -m mediagrab.core.cli "<media-url>" --audio --height 1080
.\.venv\Scripts\python.exe -m mediagrab.core.cli "<media-url>" --verbose
.\.venv\Scripts\python.exe -m mediagrab.core.cli --help
```

Replace `<media-url>` with an HTTP/HTTPS URL. Height choices are best, 2160, 1440,
1080, 720, 480, and 360; bitrate choices are best, 320, 192, and 128. `--height`
applies to video; it is accepted and ignored for audio. A direct media URL can
lack height metadata: select best when a height filter reports unavailable quality.

Playlists are off by default, including playlist-only URLs (entry 1 only). Enable
them with `--playlists`. Audio artwork is on by default and optional: failed
fetching or embedding keeps the MP3 and reports a warning. Use `--no-thumbnail`
to disable it. `--cookies-from-browser chrome`, `firefox`, or `edge` opts into the
corresponding browser session; read the privacy section before enabling it.

The CLI checks the engine's available browser impersonation targets at startup
and warns if none are available. The check is offline and nonfatal. Error messages
hide Python tracebacks by default; `--verbose` adds redacted diagnostics and engine
details. Authentication data and signed HTTP/HTTPS URLs remain redacted in verbose
output.

Ctrl+C cancels the CLI. Core downloads also accept a `threading.Event` for worker
cancellation. Network extraction and upstream FFmpeg processors check cancellation
at operation boundaries; they cannot guarantee immediate interruption of every
blocking operation. MediaGrab's own probing/conversion processes are cancellable
and reaped before returning. Completed playlist files and resumable partial
downloads are retained after cancellation.

Trailer attribution: © copyright 2008, Blender Foundation / www.bigbuckbunny.org.
Blender publishes the project under [CC BY 3.0](https://peach.blender.org/about/).
The audio example extracts the trailer soundtrack; it does not use the separately
distributed score. Downloaded media is never committed to the repository.

## Quality checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp --cov=mediagrab.core --cov=mediagrab.desktop --cov-report=term-missing
```

Tests marked `network` are skipped unless `--run-network` is passed. The network
integration test downloads the small Blender trailer as MP4 and MP3 and checks
its streams using ffprobe. Run it with both binaries available on PATH:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_network_download.py --run-network
```

Explicitly enabled integration tests fail if FFmpeg or the network is unavailable;
they do not silently skip missing dependencies. GUI tests use pytest-qt and Qt's
offscreen platform. Core coverage includes branches and must reach at least 80%.
CI enforces this threshold. Run the advisory dependency audit separately:

```powershell
.\.venv\Scripts\python.exe -m pip_audit --progress-spinner off --skip-editable
```

GitHub Actions runs lint, formatting checks, offline tests with core coverage,
and an advisory dependency audit on `windows-latest` with Python 3.14.

FFmpeg discovery checks the folder next to the running executable, the PyInstaller
bundle directory when frozen, then absolute folders on PATH. Both `ffmpeg` and
`ffprobe` must be in the same folder. Version checks run with finite timeouts and
without a shell; Windows console flags are isolated in `core/process.py`.

Video selection prioritizes resolution, then prefers H.264/AAC at the same
resolution when compatibility is enabled. The runner probes the downloaded media,
copies compatible streams, and converts incompatible video/audio to H.264/AAC
before writing metadata and reporting the final MP4. Split streams use a temporary
MKV when compatibility is enabled, allowing codecs that cannot first merge into
MP4. Conversion keeps the resolution (padding odd dimensions by one pixel), but
is lossy and costs CPU time. `--no-compatibility` keeps source codecs where MP4
supports them; playback then depends on the player's codec support. MP3 "best" maps to FFmpeg's
highest VBR quality setting, rather than a guaranteed 320 kbps stream.

## Troubleshooting

### Unsigned builds, SmartScreen and antivirus

These builds are unsigned. SmartScreen can report an unknown publisher or lack
of reputation; antivirus heuristics can flag packaged Python applications.
Such warnings alone do not establish a false positive. Download only the expected
release, retain protection, and compare SHA-256 against its published checksum:

```powershell
$zip = '.\MediaGrab-0.1.0-windows-x64.zip'
$expected = (Get-Content "$zip.sha256" -Raw).Split()[0]
$actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
if ($actual -ine $expected) { throw 'SHA-256 mismatch; do not run this archive.' }
```

A matching hash checks integrity against the selected checksum; it is not a
publisher signature or a malware guarantee. For a suspected false positive,
verify the source/release provenance and submit the file to the antivirus vendor
for review; do not disable antivirus globally.

### Packaged startup or missing resources

Re-extract the complete zip; `_internal` and bundled tool executables are required.
Use the self-check report and smoke script above. Source launches still need an
installed package and external tools. Build scripts isolate PATH to avoid native
DLLs from unrelated software. If Qt reports a missing DLL procedure, inspect
`build/mediagrab/Analysis-00.toc` and confirm no unrelated ICU/Qt DLL was collected.
The spec rejects native inputs outside Python/packages/Windows. Use the selected
64-bit Python 3.14 environment and rerun the build rather than copying DLLs from
another application. Windows 10 has not been separately tested in this phase.

### TikTok/Instagram failures or no impersonation target

Browser impersonation lets yt-dlp use browser-compatible TLS/HTTP request
fingerprints. Some sites require this capability. MediaGrab installs it through
the `yt-dlp[default,curl-cffi]` extra and explicitly requires
`curl-cffi>=0.16.0,<0.17`, within the installed engine's supported version range.
See [yt-dlp's impersonation documentation](https://github.com/yt-dlp/yt-dlp#impersonation).

If the CLI warns that no browser impersonation target is available, refresh the
project's runtime dependencies using the same Python environment that launches it:

```powershell
.\.venv\Scripts\python.exe -m pip install --editable .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m yt_dlp --list-impersonate-targets
```

Installing curl-cffi into a different Python installation does not make it
available inside `.venv`. Restart a running process after dependency changes.
Package presence alone is insufficient: the environment check inspects the
targets loaded by yt-dlp, including its native request handler.

The dependency makes supported impersonation targets available to extractors; it
does not force impersonation for every request or guarantee access to every URL.
For login-required media, authenticate in the selected browser and explicitly
enable its cookies. Private, region-restricted, and DRM-protected media retain
their existing access restrictions.

### Obtain diagnostic details

Normal CLI failures show a user-facing error without a Python traceback. Repeat
the command with `--verbose` when diagnosing a problem:

```powershell
.\.venv\Scripts\python.exe -m mediagrab.core.cli "<media-url>" --verbose
```

Verbose output retains traceback frames and redacted exception details. Review
diagnostics before attaching them to an issue; do not include cookies or signed
URLs. Desktop diagnostics rotate in `%LOCALAPPDATA%/MediaGrab/logs/mediagrab.log`
(2 MiB per file, four backups). The window shows safe messages; logs retain
redacted traceback frames without source code or local variables. Settings >
Engine/Environment provides Open logs folder and Copy diagnostics. Copied reports
include versions and capability status, excluding raw logs, executable locations,
private folder paths, cookies and signed URLs. Local panel locations are shown
for troubleshooting; log messages redact user paths and frames retain basenames.

### Environment and engine updates

Missing EJS/JavaScript/impersonation support produces warnings. Missing or broken
FFmpeg/ffprobe is an error because downloads require a working pair in one folder.
Use the panel's install commands with the Python environment launching MediaGrab.
For network failures, check the connection and retry. Login and age restrictions
require permitted browser access and explicit cookie opt-in before retrying.
Geo-blocked media must be made available by the platform; repeated retries do not
grant access. Unavailable quality: re-analyze and choose Best or another quality.

Check latest release uses the official GitHub API and official PyPI metadata via
HTTPS, five-second socket timeouts and bounded responses. The updater accepts only
stable releases inside the project's supported 2026 engine range. It verifies the
official PyPI wheel SHA-256 before pip starts; pip verifies the URL hash again.
Pip uses this interpreter, no shell, isolated configuration, the official HTTPS
PyPI index, binary-only dependencies and the project's curl-cffi bounds. Updater
output is captured and redacted in rotating logs. No automatic update occurs.

Pip installation is not transactional. After failure/cancellation run the same
venv's `python -m pip check`; repair using `python -m pip install --editable .`
if required, then restart. Test installation/cancellation in a disposable venv,
not the development venv: see [Phase 5 manual checklist](docs/NOTES.md#phase-5-manual-verification-checklist).
Frozen updating remains refused: update MediaGrab to get a newer engine.
The future engine-directory design in DECISIONS.md remains unimplemented.

## Project structure

```text
.
├── pyproject.toml
├── src/mediagrab/
│   ├── core/                 # Downloader, CLI, validation, conversion; no GUI imports
│   └── desktop/              # Interface, real workers, queue, settings, log setup, themes
├── tests/
├── scripts/                  # Verified tool downloads, build and frozen smoke
├── mediagrab.spec             # PyInstaller onedir/windowed specification
├── THIRD_PARTY_NOTICES.md     # Shipped licence text and source references
├── docs/
│   ├── DECISIONS.md
│   ├── NOTES.md
│   ├── SPEC.md
│   └── HISTORY.md
└── .github/workflows/         # Existing CI and tag-triggered Windows release
```

Core progress uses a dataclass callback and cancellation uses `threading.Event`.
The callback runs on the calling worker thread and must be fast and not raise.
The desktop layer communicates with worker threads through
Qt signals. Windows-specific integration will be isolated from the core.

## Implementation phases

| Phase | Scope | State |
| --- | --- | --- |
| 0 | Package, tooling, tests, Git hygiene, Windows CI | Implemented |
| 1 | Models, errors, validation, FFmpeg discovery, options | Implemented |
| 2 | Downloader, error mapping, cancellation, CLI, integration test | Implemented |
| 3 | Desktop layout and fake worker | Implemented |
| 4 | Real workers, queue, progress, settings, local logs and typed errors | Implemented; user manual gate passed |
| 5 | Environment checks, confirmed venv updater, disclaimer/About, diagnostics and error UX | Implemented; automated gate passed; Windows UI, diagnostics, logs and normal downloads user-verified; live updater and missing-tool simulation not run |
| 6 | Windows packaging and tagged release workflow | Implemented; local automated/frozen gate verified; release requires corresponding-source archive |
| 7 | Full documentation, screenshots, contribution guide, roadmap | Pending |

Each phase ends with README/SPEC/DECISIONS/NOTES updates, lint/test results and a commit. The next phase requires an
explicit `continue`.

## Privacy and security

The cookies-from-browser option is opt-in and disabled by default.
It allows yt-dlp to read browser session cookies and use the corresponding account
to access a platform. Cookies can grant account access: do not share them, export
them into this repository, or include them in bug reports. Engine diagnostics
redact HTTP/HTTPS URLs and suppress authentication diagnostics; traceback logging
retains frames without source code or local variables. Error messages use safe
application-owned text. Review log files before sharing them.

The implementation validates HTTP/HTTPS URLs, sanitizes output filenames,
checks output directory permissions and final path boundaries, and avoids shell
execution. MediaGrab does not implement DRM circumvention.

## Responsible use

For personal use only. Respect copyright and the Terms of Service of each
platform. The authors don't encourage downloading content you have no rights to.

## License

MediaGrab source code is licensed under [MIT](LICENSE). Bundled dependencies and
external tools retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
and the shipped `_internal/licenses` directory. Redistribution of the GPL build
requires its complete corresponding source as described in the release instructions.

## Phase 6 user verification and distribution decision — 2026-10-04

The user manually verified on Windows: extracted the zip into a clean folder,
ran MediaGrab.exe, confirmed bundled ffmpeg/ffprobe/deno detection, and completed
MP4 and MP3 downloads. This is user-reported evidence, not an automated test.
Windows 10 and live frozen Blender checks were not run. No other manual checks
are asserted by this report.

The user decided not to publish a binary Release for now: the selected Gyan
FFmpeg build is GPLv3 and includes libx264. The repository is source-only with
local build instructions; binaries are not currently distributed. The retained
release workflow requires a reviewed complete corresponding-source archive HTTPS
URL and SHA-256 via MEDIAGRAB_CORRESPONDING_SOURCE_URL and
MEDIAGRAB_CORRESPONDING_SOURCE_SHA256. Missing/invalid prerequisites or a checksum
mismatch fail the build job before artifacts reach the dependent publishing job.
Workflow inspection does not establish completeness of the supplied source.
