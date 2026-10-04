# Design decisions

## Current status and contracts

Phases 0–3 are implemented. The current request authorizes Phase 4 only.
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
- Phase 3 uses simulated analysis/downloads, real version probes, dark QSS,
  signal-only workers and an injectable queue scheduler (default 2, range 1–4).
- Phase 4 connects real workers, thumbnails, queue controls and QSettings/dialog;
  this request also brings rotating local logs and typed error UX into Phase 4.
- Phase 5 environment/JS checks, updater and first-run disclaimer remain deferred.
  Packaging/release is Phase 6; final documentation/roadmap is Phase 7.
- Default tests are offline. Verify unsure APIs against installed packages.
  Run pytest and app sequentially; pytest uses --basetemp=.pytest_tmp.
- Before every final phase commit update README, SPEC, DECISIONS and NOTES,
  validate lint/format/coverage, commit locally and stop for continue.

## Historical records

Older per-phase decisions and handoffs are preserved in [HISTORY.md](HISTORY.md).
