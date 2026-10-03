# Design decisions

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
