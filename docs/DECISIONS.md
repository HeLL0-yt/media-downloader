# Design decisions

## Current status and contracts

Phases 0–7 are implemented. Phase 4 manual Windows gate passed,
verified by the user on 2026-10-04, not by automated tests.
Phase 5's offline automated gate passed. The user verified first-run disclaimer,
About, Environment, diagnostics, logs and normal MP4/MP3 downloads on Windows;
live updater and missing-tool simulation were not run. Phase 6 frozen verification
and release prerequisites are recorded in NOTES.md. Phase 7 documentation is implemented; real screenshots remain user-supplied.
Work in the existing local checkout; no cloud, worktree, new repository or push.

- Python 3.14, Windows 10/11, PySide6, yt-dlp, native FFmpeg/ffprobe.
- Core never imports Qt or desktop. Use typed dataclasses, pathlib and logging.
- Shell-free subprocesses; Windows process flags stay in core/process.py.
- get_info(url, *, cookies_browser=None, cancel_event=None) returns VideoInfo.
  Unknown metadata stays unknown; playlists are not enumerated during analysis.
- download(request, on_progress, cancel_event) returns the actual final Path.
  ProgressEvent callbacks run on the worker thread; adapters use Qt Signals only.
- PROCESSING is distinct from success; success requires the checked final path
  and a successful engine return. Playlist progress is per stream/entry, not total.
- Cancellation uses threading.Event. Owned conversion/probe children are reaped;
  upstream extraction/FFmpeg operations stop at hooks or operation boundaries.
  Retain workers and the GUI event loop until native thread teardown completes.
- Resumable partial files and completed playlist files survive cancellation/error.
- Output checks enforce resolved destination boundaries, without claiming defense
  against hostile local filesystem races. URL allowlist covers input only.
- Compatibility defaults on: preserve resolution, prefer/convert to H.264/AAC.
  Conversion costs CPU and is lossy; HDR tone mapping is unimplemented.
- MP3 Best is VBR quality 0; explicit bitrates are 320/192/128 kbps.
  Optional artwork failure preserves MP3. Playlists default off (entry 1 only).
- Browser cookies are opt-in; never persist cookie data or log signed URLs/secrets.
  Diagnostic tracebacks retain redacted frames without source code or locals.
- Core check_environment reports yt-dlp/impersonation targets offline; its private
  upstream adapter must be reverified when upgrading the engine.
- Real AnalysisWorker calls get_info with opt-in browser and the same cancel Event.
  Analysis result keeps the existing (VideoInfo, bytes) signal; initial bytes are
  empty. A separate ThumbnailWorker reads HTTP/HTTPS with 10-second socket timeout,
  10 MiB size limit and cancellation checks. GUI decoding rejects stale snapshots.
- Stale analysis checks the submitted URL, not the canonical returned page URL.
- DownloadWorker bridges the core callback, preserving processing/progress order;
  typed exceptions produce one safe terminal signal. No widgets run on workers.
- FormatChoice accepts any positive integer height so 540p and other extracted
  heights can be selected. CLI presets and pure option-building API are unchanged.
- QueueManager defaults to real workers, concurrency 2, configurable 1–4.
  Lowering the limit lets active work finish before starting more. Retry creates
  a new worker/Event; active rows cannot be retried/removed until thread teardown.
- SettingsStore uses QSettings("MediaGrab", "MediaGrab") (Windows user registry).
  It stores defaults only, never cookie material or queue contents, and validates
  persisted values. Dialog applies saved defaults/theme immediately; existing
  queued DownloadRequest snapshots remain unchanged. Queue persistence is omitted.
- Dark/light QSS is packaged. Form rows hide inactive quality controls; percentage
  bars are centered/wider, and Download/Add to queue are the two queue buttons.
- Rotating diagnostics and typed error UX moved into Phase 4 by explicit request.
  Logs: LOCALAPPDATA/MediaGrab/logs/mediagrab.log, 2 MiB plus four backups.
  Application logging does not propagate to console; formatter redacts messages
  and complete traceback frames using core helpers. No source lines/locals/secrets.
- Close stops scheduling, sets all Events, keeps the event loop alive, and reaps
  threads only after wait(0) succeeds. It waits for upstream FFmpeg to return,
  preserving process ownership; cancellation does not force immediate shutdown.
- Production workers contain no simulation; legacy fixtures live under tests.
- Phase 5 environment/updater/disclaimer/diagnostics and Phase 6 packaging/release
  infrastructure are implemented. Phase 7 documents the existing behavior and future roadmap.
- Default tests are offline. Verify unsure APIs against installed packages.
  Run pytest and app sequentially; pytest uses --basetemp=.pytest_tmp.
- Before every final phase commit update README, SPEC, DECISIONS and NOTES,
  validate lint/format/coverage, commit locally and stop for continue.

## Phase 5 environment and updater contracts

- `core/environment.py` provides frozen EnvironmentItem/EnvironmentResult objects
  with ok/warning/error severity, detail, fix hint and optional local location.
  FFmpeg/ffprobe presence is reported individually even for incomplete pairs.
  Downloads retain the existing complete-pair requirement.
- Installed yt-dlp 2026.08.19 source verified: YoutubeDL.py documents `js_runtimes`
  as `{name: {path: executable}}` and enables only Deno by default. `_js_runtimes`
  uses `globals.supported_js_runtimes`; `utils/_jsruntime.py` defines discovery,
  version banners and MIN_SUPPORTED_VERSION. Its version subprocesses have no
  timeout. MediaGrab's offline probes use core/process with five-second timeouts
  and the installed class minimums: Deno 2.3.0, Node 22, Bun 1.2.11, QuickJS
  2023-12-09; QuickJS-ng accepts a positive version. QuickJS --help exit 1 is normal.
- Runtime discovery checks Python scripts in source mode; frozen mode prefers the
  executable directory then _MEIPASS. It searches absolute PATH folders, excludes
  implicit cwd and shell wrappers, and passes
  found executable paths explicitly for both analysis and download. This is a
  deliberate narrower search than upstream Windows cwd/PATHEXT discovery.
  Pure build_options remains free of discovery I/O. Remote EJS fetching is off.
- Environment startup and panel operations run on retained QThreads. Warnings
  never disable downloads; repair hints explain the launching environment.
- Engine release check reads official GitHub latest-stable metadata, then the
  matching official PyPI wheel identity/checksum. HTTPS redirect downgrades are
  refused. Socket timeout is five seconds; each response has a 30-second deadline
  checked between reads (an in-progress read can add one socket timeout), metadata
  limit 2 MiB and wheel limit 32 MiB. Only 2026 releases are supported by pyproject.
- Update requires explicit user confirmation, no running downloads or analysis,
  a venv, and a newer release. Re-read metadata to reject stale identity; verify
  wheel bytes against official PyPI SHA-256 before pip starts. Pip verifies the
  pinned URL hash again. No downloaded code is executed during the release check.
- Pip uses sys.executable, argument list/no shell, --isolated, disabled config via
  PIP_CONFIG_FILE=os.devnull, stripped PIP_* overrides, official HTTPS index,
  binary-only dependencies and curl-cffi>=0.16,<0.17. Installed pip configuration.py
  confirms os.devnull disables all config files even in isolated mode. Existing
  subprocess ownership/cancellation drains pipes and reaps the pip child.
- Pip updates are not atomic. Any attempted install holds scheduling/analysis
  until restart; failed/cancelled updates direct users to pip check/venv repair.
  Native teardown must follow queued result/finished delivery before releasing
  panel state. Fast analysis results similarly preserve request identity after
  native reaping, preventing dropped queued metadata signals.
- Disclaimer acceptance is versioned in QSettings (`disclaimer/accepted_v1`).
  Rejection exits; failed persistence shows a safe error and exits. Help exposes
  disclaimer and About with app/Python/Qt/engine versions, MIT and repository link.
- Logs retain existing rotation (2 MiB plus four backups); redact user paths and
  authentication/URLs, and retain traceback basenames without code/locals. Copy
  diagnostics is a structured version/status report, never raw logs or locations.

## Future frozen engine update design (not implemented)

Never run pip against the bundled interpreter or replace bundled files in place.
After explicit confirmation and while idle, fetch a versioned official release
and its official checksum manifest over HTTPS; match the exact asset SHA-256 and
reject missing/mismatched checksums. Stage only a compatible importable engine and
its pinned dependencies in `%LOCALAPPDATA%/MediaGrab/engine/<version>` with safe
archive extraction (no absolute/traversal paths), size limits and manifest records.
Validate in a separate process, then atomically switch a version pointer. At the
next startup, validate the manifest and load the selected package ahead of the
bundled copy before any yt-dlp import. Keep the last working engine and bundled
fallback; rollback on import/API failures. A user-writable directory is not a
trust boundary against a hostile local account, so verify integrity on every
load. Frozen builds refuse updates; staging, loader and rollback remain future
work, explicitly excluded from Phase 6. Packaged users update MediaGrab itself.

## Phase 6 packaging decisions

- pyproject.toml is the app version source. mediagrab.__version__ reads installed
  metadata. Build checks installed metadata against pyproject and generates PE
  version info; spec copies distribution metadata, including engine/EJS/curl/Qt.
  A missing package installation is an error, not an invented fallback version.
- Prefer onedir/windowed with _internal and no UPX. Package resources and Qt native
  libraries remain replaceable; entire directory must travel with the executable.
  Standard Windows Qt hooks remain active. Explicit platform/style/imageformat
  collection and QtSvg protect runtime plugin discovery. Do not collect all Qt
  modules just to satisfy a widget app. Plugin dependencies pull in extra Qt DLLs.
- Collect yt-dlp submodules and EJS data; installed namespace plugins are copied
  as Python files because the engine's PluginFinder scans the filesystem. The
  default build has no third-party extractor plugins. Native curl-cffi plus its
  wheel's dependent DLLs and certifi are collected; capability is tested through
  actual yt-dlp target enumeration, not package presence. Exclude build hooks and
  curl's __main__ entry point from runtime hidden imports.
- resources.resource_path resolves source package paths or _MEIPASS/mediagrab
  and rejects paths containing subdirectories/traversal. Existing About/disclaimer
  text lives in Python code and is checked through the actual frozen dialogs.
  The download-arrow ICO is generated deterministically with standard-library
  code and committed as an app asset; executable/vendor binaries stay ignored.
- FFmpeg itself provides source, not official Windows binaries. Select its linked
  Gyan essentials supplier, pinned 9.0.2 GPLv3, because compatibility conversion
  requires libx264, which LGPL builds exclude. Keep licence text, supplier README,
  configuration, source revision and component references. A source link alone is
  insufficient for this static GPL bundle. Publication fails closed until reviewed
  complete corresponding source (including linked libraries/build scripts and other
  distributed GPL/LGPL sources) is supplied via repository URL/SHA-256 variables.
  This source archive is uploaded beside the Windows zip; no release was created.
- Bundle official Deno 2.9.7 x64, MIT, rather than requiring a first-use install.
  Actual added executable size: 97,462,048 bytes; upstream zip: 42,630,221 bytes.
  Offline self-check evaluates both real EJS bundles with --no-remote/--no-npm.
  No remote EJS component is enabled and no YouTube access guarantee is claimed.
- Both fetch scripts call a typed Python helper for HTTPS downloads. Compare
  published SHA-256 with committed tool pin and hash archive before checked-path
  extraction. Cached archives are rehashed; binaries are copied fresh from verified
  archives on every build, never trusted from an unverified cached executable.
- Discovery beside sys.executable wins; frozen JS checks _MEIPASS second and ignores
  source Python scripts. Frozen update button remains disabled and direct invocation
  refuses pip with clear 'Update MediaGrab to get a newer engine' guidance.
- --self-check is Qt-free until explicit --smoke-test. JSON uses logging, never
  print; --report is dependable for noconsole. When stdout is redirected, duplicate
  its Windows handle to recover the stream cleared by the windowed bootloader.
  Report includes local paths for local verification, unlike shareable diagnostics.
  Self-check restores logger state and returns failure status.
- Isolate native analysis inside mediagrab.spec: launch wrappers can restore PATH.
  This host exposed a real collision: PyInstaller resolved Poppler icuuc.dll instead
  of Windows' unsuffixed C API. Spec searches Windows/Python/package native inputs
  and rejects foreign roots. It does not redistribute an OS DLL or patch Qt.
- The frozen check's minimal PATH retains _internal and _internal/PySide6, required
  by Qt image plugins, plus Windows/System32 and Windows. Python/system media/JS
  installations are excluded. Initial clearing of Qt's package PATH exposed SVG
  plugin loading failure; preserving those internal paths resolves that contract.
- Clean-temp smoke exercises native Windows platform (clearing offscreen), bundled
  discovery, real environment worker, themes, image formats, About/disclaimer and
  retained-thread shutdown. Temporary INI settings avoid mutating acceptance/defaults.
  Unique temp deletion is resolved and bounded to the temp root before removal.
- Release build job has read-only contents permission; a separate release job has
  contents: write. Official actions are resolved to commit hashes. Tag must match
  metadata version. Tests complete before smoke/application execution. No push,
  tag, release, cloud execution or worktree operation was performed.

## Historical records

Older per-phase decisions and handoffs are preserved in [HISTORY.md](HISTORY.md).

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

## Phase 7 documentation decisions — 2026-10-04

- Split interview-oriented architecture, development commands and detailed local
  build instructions so the README stays focused on public use.
- Use six labelled SVG placeholders, never simulated evidence; PNG captures are
  pending from the user. Cookies.txt, macOS, Telegram/web and frozen updates remain
  clearly future work. No dedicated security contact or enabled private-reporting
  configuration is invented; the policy gives a conditional private route.
- Keep release workflow unchanged: its source URL/hash and dependent job gate
  already fail closed. The maintainer supplies/reviews complete source before
  future publication. No binaries are currently distributed.
- Change descriptive project metadata only; dependencies, coverage, application,
  tests and workflows remain unchanged. All work stays in the current checkout.
