# Historical phase records

These records preserve earlier decisions and evidence verbatim. Later current
contracts in SPEC, DECISIONS and NOTES supersede historical pending statements.

## Archived design decisions

# Design decisions

## Phase 3 — 2026-10-04

The current request authorizes Phase 3 in the existing local checkout. This entry
supersedes the historical handoff's pending-phase wording. Phase 4 is not started.

### Offline desktop and reusable worker contract

The desktop shows simulated metadata and transfer/completion states explicitly.
Fake analysis validates the URL and reads a packaged SVG fixture; it performs no
HTTP requests. Fake downloads emit core ProgressEvent snapshots and create no
media or destination folders. No real core get_info/download function is wired.
Error injection is available through the immutable Simulation configuration for
tests, without assigning special behavior to user URLs.

Each worker owns a QThread and threading.Event; only immutable result/progress
payloads cross to GUI-owned Slots through Signals. QueueManager accepts a worker
factory, bounds concurrency to 1–4 (default 2), and owns workers until native
thread teardown completes. The current user request brings fake queue scheduling,
cancel/retry tests and actions into Phase 3; real engine adapters remain Phase 4.
Add to queue stages work until Start queue or Download starts the scheduler;
subsequent additions run while scheduling is active. Download adds the current
selection and starts the queue. Retry reuses the immutable request with a fresh
worker, and active rows cannot be removed or retried before thread exit.

### Asynchronous close and engine reporting

Close disables controls, stops scheduling and sets cancellation tokens. The window
keeps its event loop and worker ownership until all threads have exited. Finished
threads are checked with wait(0) and deleted on the GUI thread; no blocking GUI
wait or forced thread termination is used. The version-only probe uses core's
yt-dlp version constant and FFmpeg discovery/version functions off the GUI thread.
Core's two version subprocesses each have a five-second bound; closing can wait
for these existing probes. This is not the full Phase 5 startup environment UX.

### Presentation and settings scope

Qt 6 native high-DPI scaling uses PassThrough rounding. Packaged QSS supplies the
dark Fusion theme; visible text uses tr(), and external metadata labels use plain
text to avoid rich-text interpretation. A progress delegate distinguishes unknown
transfer progress and processing from terminal success. Context menus use popup()
and delete on hide. The thumbnail fixture is read in a worker and decoded in the
GUI. URL edits invalidate the selected metadata and stale results are discarded.
DesktopSettings holds in-memory destination/concurrency defaults only. QSettings,
settings dialogs, real thumbnails/downloads and all other Phase 4+ work remain
outside this gate. No dependencies or core source files were changed.

## Session handoff — 2026-10-04

### Scope and stop-gates

Phases **0, 1, and 2 are complete**, including the requested curl-cffi dependency,
offline impersonation capability check, and quiet CLI follow-up. **Phase 3 has not
started.** The current task updates documentation only. A new session must wait
for the user's `continue` before starting the desktop phase.

Work only in `C:\Projects\media-downloader`, using the existing local checkout.
Do not create a worktree or cloud task. Before each phase, state a short plan;
after implementation, run Ruff and pytest, make small conventional commits,
report results, and stop for `continue`. Show the working directory, the last
three commits, and Git status at the end. Do not push without authorization.
Read the repository's `AGENTS.md` before work. Resolve routine implementation
tradeoffs in this document; ask only for blocking information.

The phase entries below are historical decisions. Later entries supersede earlier
statements assigning work to a future phase. In particular, codec conversion,
optional artwork handling, and final-path checks assigned to Phase 2 in the
Phase 1 entries are now implemented.

### Fixed stack and implementation constraints

- Target Windows 10/11 and Python `>=3.14,<3.15`; macOS remains roadmap work.
- Use PySide6, yt-dlp through `import yt_dlp`, native FFmpeg/ffprobe, pytest,
  pytest-qt, Ruff, PyInstaller, PEP 621 metadata, and GitHub Actions.
- Keep `core/` independent of Qt and all GUI modules. Use typed frozen dataclasses,
  `pathlib`, logging, and Google-style docstrings for public functions.
- Never pass input to a shell: argument-list subprocesses only, `shell=False`,
  no `os.system`. Windows process flags belong only in `core/process.py`.
- Verify engine options and API behavior against installed yt-dlp source before
  adding them. Keep dependency bounds; distributed artifacts must record resolved
  versions, since ranges are not a reproducible dependency lock.
- Do not log cookies, authorization data, or full signed URLs. Preserve redacted
  traceback diagnostics for later file logging. Do not implement DRM circumvention.
- Do not commit executable binaries, downloaded media, virtual environments,
  caches, or coverage output. Preserve the MIT license and attribution.

### Contracts the desktop must preserve

`get_info(url, *, cookies_browser=None, cancel_event=None)` returns `VideoInfo`.
Analysis does not enumerate lazy playlist entries. Heights are sorted and unique;
missing duration/count/quality data stays unknown rather than fabricated.

`download(request, on_progress, cancel_event)` returns the actual final `Path`.
Its callback receives `ProgressEvent` on the calling worker thread and must be
fast and must not raise. The GUI adapter must communicate through Qt Signals,
without calling widgets from a worker. Cancellation uses `threading.Event`.
`DownloadStatus.PROCESSING` has the value `merging/converting`; transfer completion
is not overall success. Only a valid after-move path and successful engine return
permit `FINISHED`.

For playlists, the return value is the last completed final path after all entries
succeed. Progress repeats for streams and entries; it is not an aggregate playlist
percentage. Completed files and resumable partial files are retained after failure
or cancellation. Open-folder can use the request's destination for a playlist.

Compatibility defaults on: preserve resolution, prefer H.264/AAC, and convert
incompatible streams when needed. Encoding costs CPU time and is lossy; HDR tone
mapping is not implemented. MP3 uses best VBR quality 0 or 320/192/128 kbps.
Artwork defaults on and its failure preserves the successful MP3. Playlist mode
defaults off and limits playlist-only inputs to the first entry.

Cancellation is cooperative. Owned conversion/probe subprocesses are interrupted
and reaped; upstream extraction and standard processors stop at the next hook or
operation boundary. Desktop shutdown must cancel workers and wait with a timeout
without forcibly terminating a Qt thread or destroying a running worker.

Output checks create/probe a writable destination and enforce resolved boundaries
before writes and when collecting final paths. They do not protect against hostile
local processes racing changes to filesystem links. The domain allowlist applies
to the input URL, not redirects or CDN requests.

`check_environment()` currently reports only yt-dlp version, actual loaded
impersonation targets, and nonfatal warnings. It performs no HTTP requests, reads
no browser cookies, and imports no GUI. Its one private yt-dlp adapter is an
explicit compatibility maintenance point. FFmpeg/JavaScript startup reporting,
updates, rotating file logging, and first-run consent remain unimplemented.

### Remaining phase deliverables

| Phase | Required work and acceptance gate |
| --- | --- |
| 3 | Desktop layout with **fake workers only**: URL/paste/Analyze, metadata card and async thumbnail, Video/MP3 controls, quality/bitrate choices, folder picker, Add to queue/Download, queue table with progress/speed/ETA/actions and context menu, URL drag/drop and Ctrl+V, dark QSS/high-DPI support, `tr()` strings. Establish Signals-only worker communication and safe shutdown. Add offscreen main-window/fake-worker smoke tests. Do not connect real downloads in this phase. |
| 4 | Connect real analysis/download workers; queue limit defaults to 2 and is configurable 1–4; progress, cancel/retry/open-folder/remove actions. Add QSettings and settings dialog for folder, mode/quality, parallelism, compatibility, artwork, browser cookies, and dark/light theme. Queue persistence is not required. Test queue scheduling, cancellation, retry, and window creation. |
| 5 | Complete startup environment checks for engine/FFmpeg/JS runtime using then-current verified docs; show friendly warnings asynchronously. Add urllib update checks with timeouts/offline handling and development `python -m pip install -U yt-dlp`; document a safe frozen-mode update strategy before implementing it. Add first-run disclaimer, rotating `%LOCALAPPDATA%/MediaGrab/logs` logging, and polished typed-error UX. |
| 6 | PyInstaller onedir/noconsole spec, Windows build script, verified FFmpeg/ffprobe fetch/bundle script, dependency/license notices, and frozen app verification from a clean path. Add tag-triggered artifact/Release workflow; optional Inno Setup. FFmpeg's website links third-party Windows builds: do not describe those as binaries built by FFmpeg itself. |
| 7 | Final README badges, screenshot placeholders, Mermaid architecture, usage/build/troubleshooting, CONTRIBUTING, updated decisions, and roadmap for macOS/Telegram bot/web. Do not claim roadmap features are implemented. |

The first-run dialog and README must retain: "For personal use only. Respect
copyright and the Terms of Service of each platform. The authors don't encourage
downloading content you have no rights to." Browser cookie access remains opt-in;
document that it uses the user's authenticated session and can expose private
account content. All network/download work, including update checks and analysis,
must stay off the GUI thread.

## Phase 0 — 2026-10-04

### Use the existing repository root

`pyproject.toml`, `src/mediagrab/`, and the supporting directories live at the
repository root. A second `mediagrab/` project directory is unnecessary. The
existing MIT license and copyright attribution are retained.

### Separate packaging and runtime dependencies

Setuptools supplies the PEP 621 build backend. Runtime dependencies are PySide6
and `yt-dlp[default]`. The verified `default` extra includes yt-dlp-ejs, networking
dependencies, and mutagen; it does not install an external JavaScript runtime.
Testing/lint/audit tools live in the `dev` extra. PyInstaller lives in the `build`
extra and is unnecessary for running the application from source.

Dependency declarations have lower and upper version bounds. These are compatible
ranges, not a complete lock of transitive dependencies. Phase 6 must record the
resolved dependency versions used for each distributed Windows artifact.

### Target the requested Python version

The supported interpreter range is `>=3.14,<3.15`. Windows CI uses 64-bit Python
3.14. Adding macOS or another interpreter version requires separate validation.

### Test the installed package

Editable installation exposes the `src/` package. Pytest uses importlib import
mode and does not change `PYTHONPATH`. Smoke tests verify imports and distribution
metadata. A source-level import test enforces the core/GUI boundary. Static import
inspection does not detect every possible dynamic import; core must not use
dynamic imports to bypass that boundary.

Phase 0 tests validate packaging and the architectural boundary. Coverage becomes
an enforced CI check in Phase 1, when core functionality exists. Coverage
configuration already requires at least 80% and includes branch coverage.

### Keep default tests offline

Network tests require the explicit `--run-network` flag, even when selected with
`-m network`. Standard CI does not download platform content. Qt runs with
`QT_QPA_PLATFORM=offscreen` in CI.

### Limit CI permissions

CI has read-only repository permissions and does not persist checkout credentials.
Actions are pinned to commit hashes verified against their upstream `v6` tags.
Dependency auditing is visible but non-blocking, as requested. Lint, formatting,
dependency consistency, and test failures block the job.

### Add executable modules in their assigned phases

The skeleton contains package initializers and resource/script directories.
Downloader, GUI entry points, and build scripts will be added when implemented;
there are no placeholder public functions or nonfunctional launch commands.

## Phase 1 — 2026-10-04

### Immutable core data and explicit quality values

Core requests, format choices, metadata, and progress events use frozen dataclasses
with slots. Download mode and status use string enums. `None` means "best" for a
height ceiling or MP3 bitrate, and unknown for unavailable progress measurements.
Supported height ceilings and bitrates are validated at construction. Metadata
heights use a sorted unique tuple so a worker snapshot cannot be mutated after
delivery. Signed page and thumbnail URLs are excluded from dataclass repr output.

### Strict URL validation without network requests

Validation checks characters before parsing because urllib can discard control
characters. It permits HTTP/HTTPS only and rejects credentials, malformed hosts
and ports, backslashes, internal whitespace, malformed percent escapes, and raw
or percent-decoded control/formatting characters. Internationalized host names and
literal IPv4/IPv6 addresses are supported. Validation does not perform DNS or
restrict local/private hosts; this is a local desktop application.

The optional domain policy accepts bare host names and true subdomains, with a
dot boundary. IP policies match exactly. None means unrestricted, while an empty
policy denies all hosts. A malformed policy fails rather than disabling filtering.
This policy validates the input URL only; redirect/CDN enforcement is not claimed.

### Keep options construction pure

`build_options` receives validated settings, resolved executable paths, and raw
engine hooks. It performs no file creation, network requests, executable discovery,
or callback calls. Each call creates fresh nested configuration. The worker will
call `ensure_output_directory` and `ensure_ffmpeg` separately in Phase 2.

The directory check creates the destination, writes and flushes a temporary probe,
and removes it. This verifies current access; a subsequent permission or disk-space
change can still cause a download failure. The output template has fixed title/ID
fields sanitized by yt-dlp, and literal percent signs in folder names are escaped.
Phase 2 must also check captured final paths against the resolved destination.

### Preserve resolution while preferring compatible codecs

With compatibility enabled, sort fields are `res`, `vcodec:h264`, and `acodec:aac`.
Resolution takes priority; H.264/AAC win among otherwise comparable streams at
that resolution. Disabling the preference uses engine defaults. MP4 merging plus
`FFmpegVideoRemuxer` also covers single combined streams that start in another
container. The verified upstream parameter is spelled `preferedformat`.

A container is not a codec guarantee. Full compatibility requires a Phase 2
post-processing step to verify codecs and re-encode incompatible streams when the
setting is enabled. This preserves the requested resolution at the cost of CPU
time and generation loss. Re-encoding must handle source formats that cannot be
remuxed directly to MP4, and must precede final metadata processing where needed.
This is an explicit Phase 2 requirement, not completed functionality in Phase 1.

### Map MP3 best to VBR quality 0

The best MP3 choice uses `preferredquality="0"`, FFmpeg's highest VBR quality
setting supported by yt-dlp. Explicit bitrates use `"320"`, `"192"`, or `"128"`;
yt-dlp converts values above 10 into kbps encoding arguments. Increasing a target
bitrate does not restore detail absent from the source audio.

### Limit playlist-only URLs in single-video mode

`noplaylist` only resolves ambiguity between a video and its surrounding playlist.
It does not limit an input that identifies only a playlist. Single-video options
therefore also set `playlist_items="1"`. Enabling playlists removes this limit.

### Optional thumbnail failures need local handling

The builder requests `EmbedThumbnail` only for audio when enabled, writes the
thumbnail, and permits its removal after embedding. The engine has no verified
per-postprocessor ignore-failure option. Keeping `ignoreerrors=False` is necessary
to surface real download/conversion errors. In Phase 2 the runner must replace the
thumbnail processor with a best-effort wrapper that reports a safe warning, keeps
the successfully converted MP3, and preserves cancellation. A thumbnail failure
must not cause the entire audio download to fail.

### Require a complete FFmpeg pair in one directory

Discovery checks the executable's directory, `_MEIPASS` when frozen, then absolute
PATH entries. Both executables must be in one directory because `ffmpeg_location`
selects that directory for both tools. Incomplete candidates are skipped. Relative
and empty PATH entries are ignored to avoid loading tools from the current working
directory. Executable checks include access permissions; `ensure_ffmpeg` also runs
both `-version` commands with a five-second timeout each.

Release and Git snapshot version banners are accepted without an invented minimum
version. Required codec capabilities are verified by actual media operations.
The small `core/process.py` helper isolates Windows `CREATE_NO_WINDOW` handling
and uses checked argument-list execution, UTF-8 captured output, and `shell=False`.

### Enforce core coverage now

Windows CI runs the offline suite with branch coverage and the configured 80%
minimum. Real yt-dlp construction, format sorting, and filename preparation are
tested without downloading media, in addition to unit tests for validation,
settings, executable discovery, process safety, and option combinations.

## Phase 2 — 2026-10-04

### Analyze metadata without enumerating playlists

`get_info` retains the requested quiet/no-warnings/skip-download/single-video
options and calls `extract_info(download=False, process=False)`. Source inspection
showed that `lazy_playlist=True` still iterates every selected entry before
returning. Unprocessed extraction preserves a lazy entries object instead.

URL and transparent URL results are followed through the public extraction API,
with a ten-redirect limit. Transparent wrappers retain their non-null display
metadata. Playlist entries are never consumed to calculate a count: an extractor's
count or an already materialized list is used; otherwise the count is unknown.
Available heights are taken from video formats, deduplicated, and sorted. Analyze
can opt into the same browser session as downloads, with no cookie persistence.

### Capture final paths through public postprocessor registration

`YoutubeDL.download([url])` returns an exit code, not an info dictionary. The runner
registers a filename guard at the public `video` stage and a collector at
`after_move`. The collector reads the authoritative `filepath` after conversion,
metadata, optional artwork, and final moves. It accepts only nonempty existing
files with the requested extension inside the resolved destination. Transfer
`finished` hooks announce processing; only the collector plus a successful engine
exit permits the application's final `finished` event.

The public API returns one `Path`. For a playlist, it returns the last completed
entry's final path after all requested entries succeed. Progress can cycle through
transfer/processing stages for multiple streams and entries. Cancellation or a
later playlist failure retains already completed files but does not emit overall
success. The queue can open the request's output folder for playlist results.

Resolved boundary checks reject traversal and existing links that resolve outside
the destination. They are not a defense against another local process changing
links between a check and a file write. The intended destination is a user-owned
folder, not a directory writable by an untrusted competing process.

### Convert codecs before metadata, with a safe intermediate for split streams

The pure builder retains the requested MP4 merge/output options. In compatibility
mode, the `video` processor changes split-stream intermediate media to MKV before
yt-dlp chooses filenames and invokes its automatic merger. This is necessary
because automatic merger processors run before registered postprocessors: codecs
such as VP8 cannot first merge into MP4 before being converted. This temporary MKV
is converted to the requested final MP4 and removed by the engine after success.
Single combined streams go directly to the conversion processor.

The runner substitutes `VideoOutputPP` for the builder's remuxer using public
`add_post_processor`, leaving metadata processing after it. ffprobe verifies actual
streams. Compatible H.264 8-bit 4:2:0 video and AAC audio are copied; other streams
are encoded with libx264, CRF 20, medium preset, yuv420p, and AAC at 256 kbps as
needed. Conversion preserves resolution and pads odd dimensions to an even size.
Output is written to a private temporary file and atomically replaces the final
destination only after success. Failed/cancelled conversion retains the source.

Compatibility conversion is lossy and requires CPU time. HDR tone mapping and
color-fidelity guarantees are outside this phase. Disabling compatibility retains
source codecs where MP4 accepts them and leaves playback support to the player.
No global FFmpeg monkeypatches or private processor-registry replacements are used;
independent workers own separate engines, hooks, and processors.

### Keep all optional artwork work after successful MP3 conversion

The runner disables the engine's early thumbnail writing, although the pure
builder expresses the thumbnail preference. The optional processor downloads
artwork through the engine's public `urlopen` with its session and headers after
MP3 conversion/metadata. HTTP/HTTPS validation, the engine's socket timeout, a
10 MiB image limit, and cancellation checks bound that optional fetch.

Artwork is embedded using upstream `EmbedThumbnailPP` in a private MP3 copy.
Only successful embedding replaces the original. A network error, partial copy,
conversion failure, or embedding error leaves the complete MP3 intact and emits
a safe warning through both logging and a progress message. Cancellation remains
fatal to the operation. Cleanup removes only owned temporary paths; cleanup
failures are logged and do not turn a successfully saved MP3 into a failed task.
Global `ignoreerrors` remains false.

### Use cooperative cancellation and reap owned child processes

The caller supplies a `threading.Event`. Transfer hooks and all processor hooks
check it and raise upstream `DownloadCancelled`; MediaGrab maps this to its own
typed cancellation and emits one terminal cancelled event. The callback runs on
the worker's calling thread, must be fast, and must not raise. A failed callback
aborts the operation without recursively calling that same callback for an error.

MediaGrab's ffprobe/conversion commands poll cancellation while `communicate`
drains both pipes. They terminate, then kill if necessary, and reap the child before
returning. Probing has a 20-second timeout; conversion has a 24-hour limit plus
cancellation. Windows flags remain confined to `core/process.py`.

Upstream extraction requests and standard FFmpeg merging/audio/metadata/artwork
processors cannot be interrupted at every instruction by an Event. Cancellation
is checked at the next hook or operation boundary; network calls use the engine's
socket timeout. No promise of instantaneous cancellation is made. The desktop
shutdown implementation must account for these cooperative boundaries instead of
terminating a Qt thread forcibly. Retry retains resumable partial media; no broad
directory deletion occurs on cancellation.

### Map diagnostics conservatively and log safe tracebacks

Existing application errors retain their type. Typed cancellation, regional,
unsupported, browser-cookie, filesystem, network, and postprocessing causes are
mapped before extractor-message fallbacks. Explicit private/age/region/login/DRM
diagnostics take priority over generic network text. A bare 403 is a network error,
not proof that login is required. Unknown diagnostics remain a generic extraction
error. Unavailable quality advises choosing Best, useful for direct media whose
height is absent from extractor metadata. Error messages never copy raw input.

Every engine logger method redacts HTTP/HTTPS URLs and suppresses text containing
authentication diagnostics. Exception logging retains frame filenames, line
numbers, and function names without source lines or locals, and redacts exception
messages. This helper will also be used by desktop workers; rotating log-file
setup remains Phase 5 work.

### Keep real-network verification explicit

The single network integration test retrieves Blender's small Big Buck Bunny
trailer twice, for MP4 and MP3, and checks real stream codecs with ffprobe. It uses
Best because the generic extractor does not know that direct file's height before
downloading. Blender's attribution and license are recorded in NOTES and README.
The test is skipped by default and fails on missing tools/network when enabled.
Tests and manual media stay outside Git. Gyan binaries used for local verification
are checksum-verified and ignored; a distributable fetch/bundle script remains
Phase 6 work.

## Phase 2 follow-up — 2026-10-04

### Declare impersonation support and inspect actual targets

Use yt-dlp's verified `curl-cffi` extra and explicitly bound curl-cffi to the
supported 0.16 series. The extra expresses the required engine capability; the
direct bound prevents installation of older supported-but-unvalidated branches.
Both requirements participate in pip's resolver, so upstream constraint changes
must be resolved rather than bypassed.

The core environment report checks the engine's actual loaded targets, not merely
`import curl_cffi` or a distribution version. yt-dlp currently has no public target
enumeration API; its verified private method lives in one small adapter. Inspection
failure is nonfatal and produces a safe warning with diagnostic logging. Full
FFmpeg/JavaScript environment checks remain Phase 5 work.

### Suppress tracebacks only in the default CLI console

Core exception logging retains redacted full frame information and tags diagnostic
records. The CLI filters those records by default, while `--verbose` exposes them.
Filtering belongs to the CLI's handler, leaving diagnostics available to other
handlers. A copied LogRecord prevents console formatting from removing traceback
fields used by another handler. Verbose Python exception fields also use the
redaction helper; raw stack strings containing source lines are never rendered.
Logging configuration is restored at the end of each CLI invocation.

## Archived verification notes

# Verified upstream notes

## Phase 3 gate — complete, 2026-10-04

The desktop prototype is implemented in the current local checkout. Phase 4 has
not started. The historical handoff below describes the previous gate and is
superseded by this section. Stop here until the user says `continue`.

Implemented: app entry point, main window, metadata card/local demo thumbnail,
Video/MP3 controls, quality/bitrate/folder selection, clipboard and URL drag/drop,
queue table and progress delegate, buttons/context menu, fake analysis/download
workers, concurrency/cancel/retry scheduler, in-memory settings and dark QSS.
Version reporting uses core off the GUI thread. No real downloads or analysis
are connected, and the fake worker creates no files. Core remains Qt independent.

### Installed API checks and tests

Qt 6.11.2 QThread.finished/wait(0), connection enums, progress-style enums and
delegate constructors were inspected against the installed PySide6 package.
Offscreen tests exercise actual worker execution and GUI-thread Slots. Qt's
QComboBox converts a stored StrEnum to a string, so mode selection is explicitly
converted back to DownloadMode at the core request boundary. Progress painting
sets State_Horizontal. Context menus use asynchronous popup().

The installed pytest-qt teardown implementation closes and deletes registered
widgets before ordinary fixture cleanup; tests use before_close_func to finish
asynchronous worker shutdown before widget deletion. Tests cover limits 1–4,
FIFO scheduling, pending/active cancellation, fresh-worker retry after injected
failure, signal affinity, GUI timer responsiveness, action buttons/context menu,
engine-version success/failure, stale metadata, clipboard/drop, entry-point
configuration and close during analysis/active/pending work.

### Verification evidence

Windows CPython 3.14.0 and PySide6/Qt 6.11.2 in the existing `.venv`:

- Ruff lint: passed; formatting: **45 files already formatted**.
- Full offline pytest: **500 passed, 1 network test skipped** in 7.74 seconds.
- Branch-inclusive coverage: **99.14% core**, **96.49% desktop**, **98.07% combined**.
  Original core coverage configuration and 80% threshold remain unchanged.
- **25 desktop tests passed**; the core architectural import guard also passed.
- Offscreen module smoke harness ran `mediagrab.desktop.app` as `__main__`, using
  a QApplication subclass that scheduled window close, and exited **0**.
- Offscreen dark-theme render inspected locally. The offscreen plugin has no
  default font directory here; the render harness loaded installed Windows Segoe
  UI for inspection only. No font or executable was added to the application.
- No live platform requests, native interactive Windows session, frozen build or
  GitHub CI run were verified in Phase 3. The status bar correctly reports FFmpeg
  missing when its pair is not discoverable on the process PATH; ignored vendor
  binaries are not added to runtime discovery.

### Reproduce and launch (PowerShell, repository root)

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
New-Item -ItemType Directory -Force .cache/phase3 | Out-Null
.\.venv\Scripts\python.exe -m pytest --basetemp .cache/phase3/gate --cov=mediagrab.core --cov=mediagrab.desktop --cov-report=term-missing --cov-report=xml
git diff --check
Get-Location
git log --oneline -5
git status
```

Launch the native window after clearing the test-only platform override:

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m mediagrab.desktop.app
```

Analyze any valid HTTP/HTTPS URL to display labeled demo information. Add to
queue stages a request; Download adds the selection and starts scheduling;
Start queue starts already staged rows. Cancel/retry/remove operate on simulated
tasks. Open folder opens the requested destination and does not create it.

## Resume here — 2026-10-04

Read `AGENTS.md`, `docs/DECISIONS.md`, this section, and `README.md` before changing
code. Phases **0–2 are complete**; **Phase 3 is pending and requires `continue`**.
The curl-cffi/core environment/CLI follow-up is complete. This handoff adds no GUI
code. Historical phase evidence below records what was verified at each gate,
rather than a list of outstanding implementation work.

At the start of this documentation task, the checkout was clean on `main`, tracking
`origin/main` without an ahead/behind count. Baseline commit:
`3094d25 fix: declare impersonation support and quiet CLI errors`. The handoff
documentation commit follows that baseline. Recheck `git status` and `git log`
in a new session; do not infer current remote state from this dated observation.

### Implemented files and responsibilities

| Location | Implemented behavior |
| --- | --- |
| `pyproject.toml`, `.github/workflows/ci.yml` | Python/dependency bounds, editable src packaging, strict Ruff, Windows offline tests/coverage, advisory pip-audit. |
| `core/models.py`, `errors.py`, `validators.py` | Immutable request/metadata/progress contracts, typed errors, strict HTTP/HTTPS validation/domain policy, writable destination checks. |
| `core/ffmpeg.py`, `process.py`, `options.py` | Complete-pair discovery/version checks, shell-free cancellable subprocesses, pure engine options. |
| `core/downloader.py`, `postprocessors.py` | Lazy metadata analysis, downloads/cancellation, MP4 codec compatibility, optional MP3 artwork, authoritative final-path capture. |
| `core/errors_map.py`, `logging_utils.py` | Conservative friendly error mapping and redacted diagnostics. |
| `core/env_check.py`, `cli.py` | Offline actual impersonation target report, manual download CLI, default traceback suppression with `--verbose` opt-in. |
| `tests/` | Unit/mock/real-engine offline tests, architectural import guard, opt-in Creative Commons MP4/MP3 network integration. |
| `desktop/__init__.py` | Package skeleton only; no runnable desktop application yet. |

No `app.py`, main window, widgets, workers, queue manager, settings implementation,
QSS theme, engine updater, release workflow, build script, or PyInstaller spec is
implemented. Resources/scripts directories are skeletons. Full startup environment
checks, GUI smoke tests, first-run dialog, and rotating file logging remain later
phase work. See DECISIONS for the complete remaining phase gates.

### Environment and dependency baseline

Local validation uses Windows CPython **3.14.0** in repository-local `.venv`,
yt-dlp **2026.08.19**, and PySide6/Qt **6.11.2**. Runtime declarations are:

```text
PySide6>=6.11.2,<6.12
yt-dlp[default,curl-cffi]>=2026.8.19,<2027
curl-cffi>=0.16.0,<0.17
```

The project environment has curl-cffi **0.16.3** and exposed **38** impersonation
targets during the follow-up verification. Installing into another Python does
not install into this `.venv`. Missing targets are a nonfatal core/CLI warning;
the app does not force impersonation globally. The target enumeration API is
private upstream and isolated in `env_check.py`; reverify it after engine upgrades.

The `default` extra supplies yt-dlp-ejs **0.8.0**, not an external JS runtime.
The verified engine docs recommend Deno and enable it by default; other listed
runtimes require configuration. Full YouTube support is not established merely
by installing Python dependencies. Runtime detection/configuration is Phase 5.

### Commands for a new session

Run from the repository root in PowerShell. Create `.venv` with Python 3.14 if it
is absent; installation is unnecessary when the existing environment is intact.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
New-Item -ItemType Directory -Force .cache/handoff | Out-Null
.\.venv\Scripts\python.exe -m pytest --basetemp .cache/handoff/pytest --cov=mediagrab.core --cov-report=term-missing --cov-report=xml
.\.venv\Scripts\python.exe -m yt_dlp --list-impersonate-targets
git diff --check
Get-Location
git log --oneline -3
git status
```

Tests use an explicit project-local base temp because this session's sandbox
denies the default system pytest temp directory. `.cache` and coverage outputs
are ignored. Network tests are skipped unless `--run-network` is passed, including
when selected with `-m network`. With real FFmpeg/ffprobe on PATH, enable them with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_network_download.py --run-network --basetemp .cache/handoff/network
```

The local Codex command wrapper did not preserve a PowerShell PATH addition when
launching Python. For local validation using ignored `vendor/ffmpeg`, set PATH
inside Python before calling pytest:

```powershell
@'
import os
from pathlib import Path
import pytest

os.environ["PATH"] = str(Path("vendor/ffmpeg").resolve()) + os.pathsep + os.environ["PATH"]
raise SystemExit(pytest.main([
    "tests/test_network_download.py", "--run-network",
    "--basetemp", ".cache/handoff/network", "-q",
]))
'@ | .\.venv\Scripts\python.exe -X utf8 -
```

This is a validation environment workaround, not a runtime discovery change.
Create the `.cache/handoff` parent first: pytest creates the base temp itself,
but does not create missing ancestors. The initial handoff rerun failed fixture
setup because that parent was absent; the command above includes its creation.
If pip's system temp directory is also blocked, assign TEMP/TMP to a newly created
directory under `.cache` before installation. Never install project dependencies
into an unrelated interpreter to work around an environment mismatch.

Manual CLI entry point:

```powershell
.\.venv\Scripts\python.exe -m mediagrab.core.cli --help
.\.venv\Scripts\python.exe -m mediagrab.core.cli "https://download.blender.org/peach/trailer/trailer_iphone.m4v" --audio --output-dir .cache/manual
```

Options include `--height`, `--bitrate`, `--playlists`, `--cookies-from-browser`,
`--no-compatibility`, `--no-thumbnail`, and `--verbose`. Height is ignored for audio.
Use Best for direct media with unknown height metadata. Exit codes are 0 success,
1 failure, 130 cancellation, and argparse's 2 for invalid arguments. Tracebacks
are hidden by default; verbose diagnostics remain redacted.

### Verified results and limits

Latest executable-code gate: **475 passed, 1 network test skipped; 99.14% core
coverage including branches**, above the enforced 80% minimum. `env_check.py`
has 100% coverage. Ruff lint/format, `pip check`, and diff whitespace checks passed.
The documentation handoff rerun reproduced **475 passed, 1 skipped, 99.14%** after
creating the base-temp parent; Ruff and `pip check` also passed again. No source
code changed and the network test was not rerun for this documentation-only task.
The explicitly enabled network integration separately passed after curl-cffi was
added; ffprobe confirmed MP4 H.264/AAC and MP3 audio. The dependency audit reported
no known vulnerabilities and excluded the editable application itself.

Real split-stream merging/conversion and optional cover embedding were also
verified with synthetic local media. These checks do not establish every platform
or account-dependent download works. TikTok/Instagram success after manually
installing curl-cffi is user-reported, not an independently repeated platform test.
No GitHub-hosted CI run, GUI launch, or frozen application test was verified here.

Ignored `vendor/ffmpeg/` currently contains `ffmpeg.exe`, `ffprobe.exe`, and the
validation archive. Both executables report Gyan **9.0.2 essentials**; the verified
archive checksum and provenance are recorded below. They are local test tools,
not committed assets or a finished distribution. Temporary `.cache/phase2` fetch
and synthetic-pipeline helpers are not maintained product scripts. A new session
must not depend on ignored files being available on another machine.

### Resume checklist

1. Inspect local status and preserve any user changes; use the current files as
   authority and the historical notes as evidence.
2. Confirm the requested phase. The next authorized phase after `continue` is
   **Phase 3: desktop layout and fake workers**, with no real download integration.
3. Reuse the existing core contracts. Keep network work off the GUI thread, bridge
   callbacks through Signals, and design cooperative worker shutdown before wiring
   real downloads in Phase 4.
4. Run the checks above, record new evidence, commit the phase, and stop. Do not
   present future UI, updater, packaging, or roadmap work as completed.

## Phase 0 — 2026-10-04

Dependency metadata was checked against PyPI and the local Python 3.14 environment.

| Package | Verified release | Declared range |
| --- | --- | --- |
| PySide6 | 6.11.2 | `>=6.11.2,<6.12` |
| yt-dlp | 2026.8.19 | `>=2026.8.19,<2027`, with `default` extra |
| pytest | 9.1.1 | `>=9.1.1,<10` |
| pytest-qt | 4.5.0 | `>=4.5.0,<5` |
| pytest-cov | 7.1.0 | `>=7.1.0,<8` |
| ruff | 0.16.10 | `>=0.16.10,<0.17` |
| PyInstaller | 6.22.3 | `>=6.22.3,<7` |
| pip-audit | 2.10.1 | `>=2.10.1,<3` |
| setuptools | 84.0.0 | `>=84.0.0,<85` |

Sources: [PySide6](https://pypi.org/project/PySide6/6.11.2/),
[yt-dlp](https://pypi.org/project/yt-dlp/2026.8.19/),
[pytest](https://pypi.org/project/pytest/9.1.1/),
[pytest-qt](https://pypi.org/project/pytest-qt/4.5.0/),
[pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/),
[ruff](https://pypi.org/project/ruff/0.16.10/),
[PyInstaller](https://pypi.org/project/pyinstaller/6.22.3/),
[pip-audit](https://pypi.org/project/pip-audit/2.10.1/),
[setuptools](https://pypi.org/project/setuptools/84.0.0/).

### YouTube JavaScript support

The [yt-dlp 2026.08.19 README](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/README.md#dependencies)
states that full YouTube support requires yt-dlp-ejs and a supported external
JavaScript runtime. Deno is recommended; Node.js, Bun, and QuickJS are also listed.
Only Deno is enabled by default. Merely detecting another runtime does not mean
yt-dlp is configured to use it.

The installed `yt-dlp` distribution metadata confirms that its `default` extra
requires `yt-dlp-ejs==0.8.0`. MediaGrab uses that extra. Phase 5 will verify runtime
availability and versions against the then-installed engine, explicitly configure
supported runtimes, and display missing-component warnings. No runtime download
or runtime execution is added in Phase 0.

FFmpeg and ffprobe are external executables required for merging and audio
conversion. The upstream README explicitly distinguishes these binaries from
Python packages named ffmpeg.

### CI action references

The upstream GitHub API tag references were checked before pinning:

- [actions/checkout v6](https://github.com/actions/checkout/tree/d23441a48e516b6c34aea4fa41551a30e30af803)
- [actions/setup-python v6](https://github.com/actions/setup-python/tree/ece7cb06caefa5fff74198d8649806c4678c61a1)

yt-dlp library option names will be verified against installed source before
implementing the options builder in Phase 1.

### Local Phase 0 validation

Validation used Windows, CPython 3.14.0, and the repository-local `.venv`:

- Editable installation with the `dev` extra succeeded.
- `pip check`: no broken requirements.
- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `pytest` with offscreen Qt: 5 passed.
- `pip wheel . --no-deps --no-build-isolation`: succeeded. Wheel contents include
  the package modules, `py.typed`, and the MIT license, and exclude tests and the
  virtual environment.
- `pip-audit --skip-editable`: no known vulnerabilities found in installed
  dependencies. The editable application itself is excluded from this dependency
  audit; this does not establish that application code is vulnerability-free.

The GitHub-hosted CI run has not been executed locally. Core behavior and GUI
smoke tests will be added in their assigned phases.

## Phase 1 — 2026-10-04

Options were checked against the installed yt-dlp 2026.08.19 distribution before
implementation. The primary references are:

- [`YoutubeDL.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/YoutubeDL.py):
  library option documentation for output templates, filename sanitization,
  retries, concurrent fragments, cookies, transfer/postprocessor hooks, playlist
  handling, format sorting, `final_ext`, and `ffmpeg_location`.
- [`ffmpeg.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/ffmpeg.py):
  `FFmpegExtractAudioPP` quality mapping, MP4 remuxer, and metadata processor.
- [`embedthumbnail.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/embedthumbnail.py):
  thumbnail processing, cleanup, and failure behavior.
- [`__init__.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/__init__.py):
  the upstream CLI-to-library translation confirms processor dictionaries and
  the spelling `preferedformat`.
- [`FormatSorter`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/utils/_utils.py):
  confirms `res`, `vcodec:h264`, and `acodec:aac` as supported sort fields.

`noplaylist` is documented as selecting a single video "if in doubt". The builder
also selects playlist entry 1 when playlists are disabled, so a playlist-only URL
cannot implicitly download all entries.

An MP4 output container does not ensure H.264/AAC playback compatibility. The
upstream remuxer copies streams. The resolution-preserving codec preference is
covered by an offline test using the actual installed engine. Additional codec
verification/conversion is assigned to the Phase 2 download runner.

Upstream `run_pp` re-raises `PostProcessingError` unless global `ignoreerrors` is
True. There is no per-processor flag to make `EmbedThumbnail` optional. Phase 2
therefore requires a local wrapper; the builder retains `ignoreerrors=False`.

Python's [URL parsing security documentation](https://docs.python.org/3.14/library/urllib.parse.html#url-parsing-security)
warns that parsing alone does not validate a URL. Raw controls are checked before
calling `urlsplit`, and URL structure/domain rules are checked explicitly.

No media downloads or real FFmpeg conversions were performed in Phase 1. Tests
use temporary executable placeholders and mocked process results for discovery
and version checks. Real media processing belongs to Phase 2 integration testing.

### Local Phase 1 validation

Windows CPython 3.14.0, yt-dlp 2026.08.19, PySide6/Qt 6.11.2:

- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `pytest --cov=mediagrab.core --cov-report=term-missing --cov-report=xml` with
  offscreen Qt: **314 passed**, **99.12% core coverage including branches**.
- All requested height ceilings, bitrates, and playlist settings are covered.
- Offline real-engine checks cover postprocessor registration, format-selector
  parsing, resolution/codec ordering, filename traversal prevention, and literal
  percent signs in the destination.
- `git diff --check`: passed.

The 80% coverage threshold is now enforced by Windows CI. The GitHub-hosted job
itself has not been run as part of this local phase.

## Phase 2 — 2026-10-04

### Verified engine behavior

The installed yt-dlp **2026.08.19** source was read before using the extraction,
hook, processor, and networking APIs:

- [`YoutubeDL.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/YoutubeDL.py):
  `extract_info(download=False, process=False)`, URL result processing,
  `add_post_processor`, stage ordering, automatic merger ordering, download exit
  codes, final `filepath` updates, thumbnail writes, and `logger` options.
- [`common.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/common.py):
  custom `PostProcessor.run` contract and progress hooks. Hook info copies are
  made before the processor runs, so a finished hook can carry a stale filepath.
  The after-move collector reads the actual updated info instead.
- [`ffmpeg.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/ffmpeg.py):
  merger container selection, audio conversion, metadata, and FFmpeg argument
  handling. Automatic merging precedes registered conversion processors.
- [`embedthumbnail.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/embedthumbnail.py):
  optional artwork conversion, file replacement, and temporary file names.
- [`networking`](https://github.com/yt-dlp/yt-dlp/tree/2026.08.19/yt_dlp/networking):
  public `Request` and `YoutubeDL.urlopen` for optional artwork using the existing
  engine session, rather than a separate unauthenticated HTTP client.
- [`FFmpeg documentation`](https://ffmpeg.org/ffmpeg.html): stream mapping,
  codec copy versus encoding, and output-container handling.

`lazy_playlist` does not mean Analyze can return without walking entries. The
installed `__process_playlist` still enumerates them. Unprocessed extraction plus
bounded URL-result resolution avoids that walk. An offline test registers a real
InfoExtractor with a generator that fails if consumed, proving the boundary.

### Integration media and attribution

The integration test uses the **3,889,885-byte** Big Buck Bunny trailer hosted at
[Blender's download server](https://download.blender.org/peach/trailer/trailer_iphone.m4v).
[Blender's license page](https://peach.blender.org/about/) identifies published
Peach project content as Creative Commons Attribution 3.0 and specifies attribution.
For the trailer and its extracted soundtrack:

**© copyright 2008, Blender Foundation / www.bigbuckbunny.org.**

The test extracts the soundtrack from this trailer, not the separately released
score. It downloads into pytest's temporary directory and commits no media.
This test exercises a generic direct-media extractor; it does not establish that
every platform works or that YouTube's runtime/authentication needs are satisfied.

W3C's Sintel copy was also considered. Its GET request succeeded with urllib,
but the installed engine encountered an anti-bot 403. The integration fixture
therefore uses Blender's trailer, which passed with the engine's default requests.
No anti-bot bypass or forced impersonation was added.

### Local executable verification

[FFmpeg's download page](https://ffmpeg.org/download.html) links third-party
Windows builds, including [Gyan](https://www.gyan.dev/ffmpeg/builds/). The validation
tools were downloaded into the ignored project-local `vendor/ffmpeg/` directory.
They are not committed or packaged in this phase.

The publisher's [essentials checksum endpoint](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256)
resolved to the versioned `ffmpeg-9.0.2-essentials_build.zip.sha256`. The matching
versioned archive was used, rather than independently fetching a moving latest
archive. Its SHA-256 was verified before selectively copying only the two named
executables:

```text
60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba
```

Both binaries report `9.0.2-essentials_build-www.gyan.dev`. The checksum checks
archive integrity against the publisher's HTTPS checksum; it is not an independent
publisher-signature verification. Packaging and dependency-license notices remain
Phase 6 work.

### Local Phase 2 validation

Windows CPython 3.14.0, yt-dlp 2026.08.19, PySide6/Qt 6.11.2:

- `ruff check .` and `ruff format --check .`: passed.
- Offline pytest with branch-inclusive core coverage: **460 passed, 1 network
  test skipped**, **99.08% core coverage**.
- Explicitly enabled network integration: **1 passed**. Real MP4 had H.264/AAC;
  real MP3 had an MP3 audio stream, verified with ffprobe.
- Manual CLI downloaded and returned Blender's final MP4 path.
- Real synthetic VP9/Opus conversion produced H.264/yuv420p/AAC MP4.
- Real separate VP8 and Opus streams went through yt-dlp's automatic merger,
  the compatibility intermediate, codec conversion, metadata, and final path
  collector; ffprobe confirmed H.264/AAC.
- Real optional JPEG embedding produced an MP3 with an attached cover image.
- Native subprocess tests verify both pipes are drained and children are reaped
  on cancellation/timeouts, including a forced-kill fallback.

The sandbox denies pytest's default system temp directory. Local test runs use
`--basetemp .cache/phase2/pytest` within the project; ordinary developer/CI runs
can use the default directory. All binaries, media, temporary test data, and
coverage outputs are ignored. The GitHub-hosted workflow has not been run locally.

## Phase 2 follow-up: impersonation dependency and CLI diagnostics — 2026-10-04

The installed yt-dlp **2026.08.19** distribution metadata was checked directly.
It declares `Provides-Extra: curl-cffi` and this requirement:

```text
curl-cffi!=0.6.*,!=0.7.*,!=0.8.*,!=0.9.*,<0.17,>=0.5.10;
    (implementation_name == 'cpython') and extra == 'curl-cffi'
```

The installed README also recommends `yt-dlp[default,curl-cffi]` for browser
impersonation. The installed `_curlcffi.py` handler accepts 0.5.10 and 0.10.x
through 0.16.x, and rejects unsupported versions. Sources:

- [yt-dlp impersonation documentation](https://github.com/yt-dlp/yt-dlp#impersonation).
- [Pinned handler source](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/networking/_curlcffi.py).
- [Pinned engine source](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/YoutubeDL.py).
- [curl-cffi 0.16.3 release files](https://pypi.org/project/curl-cffi/0.16.3/#files).

Runtime requirements now include `yt-dlp[default,curl-cffi]>=2026.8.19,<2027` and
the explicit bound `curl-cffi>=0.16.0,<0.17`. The extra identifies the engine
capability; the direct requirement narrows its broad legacy-compatible range to
the verified modern 0.16 series. Upstream's `pin-curl-cffi` extra pins 0.16.0, which
supports this lower bound choice. The upper bound matches the installed handler's
compatibility ceiling; releases 0.17 and later require a fresh compatibility check.

PyPI metadata for 0.16.0 and 0.16.3 was verified before installation. The project
environment installed the `cp310-abi3-win_amd64` wheel for curl-cffi **0.16.3** under
CPython 3.14.0, along with cffi **2.1.1** and pycparser **3.0**. The project `.venv`
initially lacked curl-cffi; a manual install into another interpreter does not
apply to an isolated virtual environment. Source installation now installs this
dependency without a separate manual command.

### Capability check

`core/env_check.py` reports the engine version, sorted unique impersonation target
names, and nonfatal warnings. It initializes an engine without extractors and
enumerates loaded handlers without making HTTP requests or reading browser cookies.
Missing targets produce an actionable reinstall/restart warning; initialization,
native-handler, or API failures produce a safe warning plus a redacted diagnostic.

The installed engine exposes `_get_available_impersonate_targets()` and marks a
public API as a future TODO. That private call is isolated in one adapter; it is
not an invented yt-dlp option. Tests exercise missing/broken handlers and confirm
the installed engine exposes targets while `urlopen` is prohibited. After adding
the declared dependency, the local Windows engine exposes **38 targets** with no
environment warning. The check does not force a target for all downloads.

### Console diagnostics

The CLI emits environment warnings before starting a download. Its console handler
suppresses explicitly tagged core traceback diagnostics unless `--verbose` is
passed. Verbose mode also shows redacted engine debug messages and the capability
summary. Python exception fields are formatted through the core redaction helper;
raw stack source lines and locals are excluded. Traceback records remain available
to other application log handlers, including the later desktop logging setup.
CLI logging configuration is restored after the command returns.

This change stays in Phase 2/core/CLI. No desktop or Phase 3 files are changed.
TikTok/Instagram success after manual curl-cffi installation was reported by the
user; this follow-up does not independently test account-dependent platform URLs.

### Follow-up validation

- Declared dependencies installed successfully in the project `.venv`; `pip check`
  reports no broken requirements.
- `ruff check .` and `ruff format --check .`: passed.
- Offline pytest: **475 passed, 1 network test skipped**, **99.14% core coverage
  including branches**. The new environment module has **100% coverage**.
- Explicit MP4/MP3 Creative Commons network integration: **1 passed** after adding
  curl-cffi, with real ffprobe stream checks.
- Real CLI failure against a deliberately blocked local destination: no traceback
  by default; redacted traceback with `--verbose`; URL query tokens absent in both.
  Terminal failures are printed once instead of duplicating the callback and
  exception messages.
- `pip-audit --skip-editable`: no known vulnerabilities found in installed
  dependencies. The editable application is excluded from this dependency audit.
- Engine's `--list-impersonate-targets`: **38 available targets**.
