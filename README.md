# MediaGrab

MediaGrab is a Python 3.14 desktop application being built for Windows 10/11.
Its download engine uses yt-dlp as a library, FFmpeg for media processing,
and PySide6 for the interface.

**Current status: Phases 0–4 implemented. Phase 4 automated checks are complete;
manual platform checks are pending. Phase 5 has not started.**

## Existing features

- Real desktop and CLI metadata extraction and MP4/MP3 downloads through yt-dlp.
- Metadata card with title, uploader, duration and asynchronous optional thumbnail.
  Video quality choices come from reported heights; Best handles unknown heights.
- Queue with 1–4 parallel downloads (default 2), per-task progress/speed/ETA,
  cancel, retry, remove and open folder.
- QSettings preferences for default folder, mode/video quality/audio bitrate,
  parallelism, H.264/AAC compatibility, MP3 artwork, opt-in browser cookies and
  dark/light theme. Queued requests retain the settings used when added.
- Safe typed error messages and rotating redacted local diagnostic logs.
- Clipboard/URL drag-drop input and cooperative shutdown that waits for workers.

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
folder to PATH. Automated bundling belongs to Phase 6. YouTube's external
JavaScript runtime requirements and the startup check belong to Phase 5.

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
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp --cov=mediagrab.core --cov-report=term-missing
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
redacted traceback frames without source code or local variables. Full startup
checks remain Phase 5 work.

## Project structure

```text
.
├── pyproject.toml
├── src/mediagrab/
│   ├── core/                 # Downloader, CLI, validation, conversion; no GUI imports
│   └── desktop/              # Interface, real workers, queue, settings, log setup, themes
├── tests/
├── scripts/                  # Windows build scripts, added in Phase 6
├── docs/
│   ├── DECISIONS.md
│   ├── NOTES.md
│   ├── SPEC.md
│   └── HISTORY.md
└── .github/workflows/ci.yml
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
| 4 | Real workers, queue, progress, settings, local logs and typed errors | Implemented |
| 5 | Full environment checks, updater, first-run disclaimer | Pending |
| 6 | Windows packaging and tagged release workflow | Pending |
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
external tools retain their own licenses; distribution notices will be addressed
in the Windows packaging phase.
