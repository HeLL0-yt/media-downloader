# Design decisions

## Current status and contracts

Phases 0–4 are implemented. Phase 4 awaits manual checks and user continue.
Phase 5 is not started.
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
- Phase 5 environment/JS checks, updater and first-run disclaimer remain deferred.
  Packaging/release is Phase 6; final documentation/roadmap is Phase 7.
- Default tests are offline. Verify unsure APIs against installed packages.
  Run pytest and app sequentially; pytest uses --basetemp=.pytest_tmp.
- Before every final phase commit update README, SPEC, DECISIONS and NOTES,
  validate lint/format/coverage, commit locally and stop for continue.

## Historical records

Older per-phase decisions and handoffs are preserved in [HISTORY.md](HISTORY.md).
