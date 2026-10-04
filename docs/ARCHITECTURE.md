# Architecture

MediaGrab separates a synchronous Python download core from a Qt desktop adapter.
The CLI calls the same core as desktop workers. This allows a future bot or web
adapter to reuse contracts without importing widgets; those adapters do not exist
yet. [DECISIONS.md](DECISIONS.md) records detailed constraints and
[NOTES.md](NOTES.md) distinguishes automated evidence from manual checks.

## Core contracts

`core/models.py` defines frozen dataclasses with slots. `DownloadRequest` captures
URL, destination, `FormatChoice`, playlist/compatibility/artwork flags and optional
browser-cookie preference. `VideoInfo` contains plain metadata; unknown duration,
height and counts remain unknown. `ProgressEvent` carries status, transfer bytes,
speed, ETA and optional path. URL fields are excluded from representations.

`get_info(url, *, cookies_browser=None, cancel_event=None)` returns `VideoInfo`.
Analysis resolves redirects but avoids enumerating lazy playlist entries. Desktop
quality choices use reported heights; `FormatChoice` accepts positive height
ceilings, while the CLI offers fixed presets.

`download(request, on_progress, cancel_event)` returns the checked final `Path`.
The callback runs synchronously on the calling thread and must remain fast and
not raise. Core validates input/output, creates pure engine options, configures
tools and drives yt-dlp hooks/postprocessors. A processing event does not mean
success: the engine must finish successfully and the final file must exist within
the destination. Playlist callbacks describe individual streams/entries rather
than aggregate playlist completion; the returned path is the last completed file.

`options.py` builds options without discovery I/O. `postprocessors.py` manages
output guards, final paths, optional MP3 artwork and compatibility conversion.
Compatibility prefers H.264/AAC at the selected resolution and converts when
needed. Compatible streams are copied; incompatible streams are encoded. Odd
dimensions can be padded by one pixel. Conversion costs CPU and is lossy;
HDR tone mapping is not implemented. Artwork failure preserves the MP3.

## Threading and scheduling

Widgets, mutable queue state and scheduling live on the GUI thread.
`desktop/workers.py` uses QThread subclasses whose `run()` methods call core.
Workers receive immutable requests and own `threading.Event` cancellation tokens;
they emit Qt signals rather than touching widgets.

`AnalysisWorker` emits metadata before artwork. A separate `ThumbnailWorker`
fetches at most 10 MiB using a 10-second socket timeout; GUI decoding rejects
stale metadata snapshots. Analysis results are checked against the submitted URL,
not only the canonical URL returned by the engine.

`DownloadWorker` bridges progress to `(job_id, ProgressEvent)` signals and maps
exceptions to one safe terminal event. `QueueManager` limits active workers to
1–4, default 2. Lowering the limit lets active work finish. Retry creates a fresh
worker and Event only after the old worker exits. Changing defaults does not
mutate existing requests. The queue is in memory; QSettings saves defaults and
disclaimer acceptance, not task contents.

The native thread can still be tearing down when Qt's `finished` signal arrives.
Owners keep references, poll `wait(0)` through timers and call `deleteLater()`
after completion. Result signal delivery and worker cleanup are ordered to avoid
losing fast results or releasing engine scheduling too early.

## Cancellation and shutdown

Cancel sets an Event. Queued tasks cancel immediately; running core operations
observe cancellation at hooks and operation boundaries. MediaGrab-owned probe
and conversion subprocesses are cancelled, drained and reaped through
`core/process.py`. yt-dlp-owned extraction and FFmpeg operations can block until
their own operation returns. Immediate cancellation is not guaranteed.

Close stops scheduling, requests all cancellations and retains workers and the
GUI event loop until teardown completes. No forced QThread termination occurs.
Completed playlist files and resumable partial files survive failure/cancellation.
This prioritizes resource ownership and recoverable output over instant exit.

## Errors, logging and trust boundaries

`errors.py` provides application error types. `errors_map.py` inspects exception
chains, prioritizes typed causes, then uses engine-message rules for DRM, private,
age, geographic, login, unsupported URL, unavailable format, FFmpeg, network and
postprocessing failures. Unknown errors receive generic extraction guidance.
Message matching is an integration trade-off and needs revalidation after engine
changes. Widgets display application-owned messages, not raw engine exceptions.

`logging_utils.py` redacts URLs, authentication material and user paths. Desktop
logs rotate at 2 MiB with four backups; traceback frames retain basenames without
source lines/locals. Copy diagnostics is a structured status/version report,
excluding raw logs and paths. Local deployment reports intentionally include paths.

HTTP/HTTPS input validation rejects credentials/control characters; private hosts
are allowed. Output paths are sanitized and checked against resolved destination
boundaries. This is not protection against hostile local filesystem races or a
server network isolation policy. Subprocesses use argument lists, without a shell;
Windows process flags are isolated in `process.py`. Browser cookies remain opt-in.

## Environment checks and engine updates

`environment.py` returns immutable severity/detail/location/fix-hint items.
Checks are offline: package versions, complete FFmpeg pairs, finite version probes,
supported JavaScript tools and real impersonation targets. Runtime minimums come
from installed yt-dlp classes. Source discovery checks Python scripts and absolute
PATH folders; frozen discovery prefers executable/bundle folders. Implicit cwd
and shell wrappers are excluded. Found paths are explicitly supplied to the
engine; remote EJS fetching is disabled. Warnings remain nonfatal.

Environment and updater calls run on retained engine workers. Release checks are
explicit and use official GitHub/PyPI HTTPS metadata, bounded response sizes and
timeouts, rejecting insecure redirects and releases outside dependency bounds.
Installation requires confirmation, an idle app, a virtual environment and a newer
supported release. Metadata is revalidated; the wheel's official SHA-256 is checked
before pip. Pip uses the current interpreter, isolated configuration, official
index, binary-only dependencies and project curl-cffi bounds, with captured
redacted output. Pip installation is not atomic: any attempt requires restart,
and failure/cancellation requires environment inspection/repair.

System and frozen updates are refused. A future frozen update design in
[DECISIONS.md](DECISIONS.md#future-frozen-engine-update-design-not-implemented)
uses staged verification, a version pointer and rollback; none of that loader is
implemented.

## Frozen Windows build

`mediagrab.spec` creates a windowed onedir bundle without UPX. Installed metadata
supplies the version; the build rejects stale metadata. `resources.py` resolves
source package resources or `_MEIPASS` without relying on working directory.
The build collects extractors, EJS, native impersonation libraries, CA certificates,
Qt plugins, themes and notices. Installed namespace plugins are copied as files
for the engine's finder; the default build contains no third-party extractors.

Pinned tool downloads compare published/committed hashes, verify archives and
extract into ignored vendor storage. FFmpeg/ffprobe/Deno live beside the exe.
Native dependency search is isolated to avoid unrelated developer DLLs; Phase 6
found and fixed a Poppler ICU collision. The entire folder must travel together.
Offline `--self-check` exercises real resources/tools/EJS; separate native Windows
GUI smoke runs from a clean temporary copy with minimal PATH and temporary INI
settings. These deployment checks run outside pytest. See [Building](BUILDING.md).

Binaries are not currently distributed. The Gyan build includes libx264 and is
GPLv3. The retained release workflow requires a reviewed complete corresponding-
source archive and matching SHA-256 before the dependent publishing job can run.
Checking the hash does not itself establish source completeness.

## Design decisions and trade-offs

| Decision | Reason and cost |
| --- | --- |
| Synchronous core with callbacks/Event | Reusable outside Qt; adapters manage threads and cancellation latency. |
| Immutable request snapshots | Predictable queued behavior; changes to defaults require new tasks. |
| QThreads plus signals | GUI stays responsive; native teardown and queued result ordering need explicit ownership. |
| Compatibility enabled by default | Broad H.264/AAC playback; encoding consumes CPU and loses quality. |
| Onedir, bundled Deno, no UPX | Offline tooling and replaceable components; larger local distribution folder. |
| Opt-in cookies, conservative diagnostics | Reduced accidental credential exposure; account access still needs user consent and log review. |
| Confirmed venv updater only | Limits changes to a supported environment; no atomic install or frozen update today. |
| Source-only publication | Local packaging remains available while complete GPL/LGPL source prerequisites are unresolved. |
