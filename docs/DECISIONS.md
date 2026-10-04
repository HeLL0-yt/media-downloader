# Design decisions

## Current status and contracts

Phases 0–5 are implemented. Phase 4 manual Windows gate passed,
verified by the user on 2026-10-04, not by automated tests.
Phase 5's offline automated gate is passed; manual verification instructions are
in NOTES.md. Phase 6 has not started.
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
- Phase 5 environment/updater/disclaimer/diagnostics are implemented.
  Packaging/release remains Phase 6; final documentation/roadmap remains Phase 7.
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
- Runtime discovery checks Python scripts, the executable directory when frozen,
  and absolute PATH folders, excludes implicit cwd and shell wrappers, and passes
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
load. Frozen builds currently refuse updates; packaging compatibility, staging,
loader and rollback tests belong to the later packaging work.

## Historical records

Older per-phase decisions and handoffs are preserved in [HISTORY.md](HISTORY.md).
