# MediaGrab project specification

Target Windows 10/11, Python 3.14, PySide6, yt-dlp and native FFmpeg/ffprobe.
Work in the existing local repository. Core must remain independent of Qt and
desktop. Use typed dataclasses, pathlib, logging, and shell-free subprocesses.
This specification consolidates the supplied phase requirements and the existing
DECISIONS/NOTES contracts; no separate PROJECT SPEC section was supplied.

## Completed phases

- **Phase 0 — done:** src packaging, dependency bounds, Windows CI and offline tests.
- **Phase 1 — done:** immutable models, typed errors, URL/destination validation,
  FFmpeg discovery/version checks and pure yt-dlp options.
- **Phase 2 — done:** metadata extraction, downloads, cancellation with
  threading.Event, error mapping, H.264/AAC compatibility conversion, optional
  MP3 artwork, manual CLI, curl-cffi impersonation support, offline capability
  checks and quiet CLI tracebacks unless --verbose.

## Phase 3 acceptance gate

Build desktop/app.py, main_window.py, widgets.py, workers.py, queue_manager.py,
settings.py and resources. Use fake analysis/download workers only, with no media
requests or writes. Clearly identify simulated metadata and progress in the UI.

- URL input, paste, Analyze, URL drag/drop and Ctrl+V.
- Metadata card with thumbnail, title, uploader and duration.
- Video/MP3 selection, video quality, audio bitrate, output folder picker,
  Add to queue and Download.
- Queue columns: Title, Mode, Quality, Status, delegated progress bar, Speed,
  ETA and Actions; cancel, retry, open folder and remove through buttons/menu.
- Status bar reads yt-dlp and FFmpeg versions through core off the GUI thread.
- Dark QSS, Qt high-DPI support and tr() for user-facing strings.
- Background workers communicate exclusively through Signals. Fake downloads
  emit the core ProgressEvent including finished/error/cancelled states.
- Queue parallel limit, cancel/retry and clean cooperative shutdown, retaining
  ownership until every worker has exited; never terminate a Qt thread.
- pytest-qt offscreen tests for creation, scheduling, signals and shutdown.
  Preserve core coverage configuration and pass Ruff lint/format and pytest.
- Provide python -m mediagrab.desktop.app. Make small conventional local commits,
  update DECISIONS/NOTES and stop for the user's continue at this gate.

## Remaining roadmap (not Phase 3 work)

4. Real analysis/download adapters, settings dialog and QSettings; folder,
   mode/quality, parallelism 1–4, compatibility, artwork, browser cookies, theme.
5. Full environment/JS/impersonation checks, updater, first-run disclaimer,
   rotating local logs and polished error UX.
6. PyInstaller onedir/noconsole, verified binary fetch/build scripts, clean-path
   validation and Windows release workflow; never commit executable binaries.
7. Final README, badges/screenshots/architecture/usage/build/troubleshooting,
   CONTRIBUTING and macOS/Telegram/web roadmap.

For personal use only. Respect copyright and the Terms of Service of each
platform. The authors don't encourage downloading content you have no rights to.
Browser-cookie access remains opt-in. No DRM circumvention.

## Core contracts

get_info returns VideoInfo; download returns the actual final Path and calls
on_progress with immutable ProgressEvent on its calling worker thread.
threading.Event cancellation is cooperative. Processing is distinct from success.
Unknown metadata remains unknown. See DECISIONS.md for detailed path, playlist,
compatibility, logging and cancellation constraints; NOTES.md records evidence.
