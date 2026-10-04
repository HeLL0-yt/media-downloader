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

## Completed desktop phases

- **Phase 3 — done, 2026-10-04:** desktop layout, signal-only simulated workers,
  bounded queue, progress/actions, dark theme, clipboard/drop and safe shutdown.
  Original acceptance/evidence is preserved in HISTORY.md.
- **Phase 4 — implemented, 2026-10-04:** real get_info/download adapters, metadata
  and separate optional thumbnail fetch, all reported video heights, real queue
  defaulting to 2 with settings range 1–4, progress/speed/ETA and row actions.
  QSettings-backed dialog persists folder, mode/quality/bitrate, parallelism,
  compatibility, artwork, opt-in cookies and dark/light theme. Typed errors and
  rotating redacted logs were explicitly brought into this phase by the user.

Phase 4 UI acceptance: one aligned field grid, conditional video/audio quality
rows, wide progress bars with centered percentages, Download and Add to queue
buttons, and more vertical room for the queue. Core remains independent of Qt.
Download adds and starts; Add to queue stages or joins an already running queue.
Workers communicate through immutable signal payloads. Close cancels and retains
all workers until native thread completion; no forced termination or abandonment
of upstream FFmpeg operations. Cancellation remains cooperative.

Phase 4 automated gate: Ruff lint/format and sequential pytest-qt offscreen with
mocked core calls, coverage and --basetemp=.pytest_tmp. Default tests make no media
network requests. Manual user gate: 1080p MP4 and MP3 on YouTube/TikTok/Instagram,
cancel mid-download, invalid URL, offline failure and close during download.
The user manually verified this Windows gate as passed on 2026-10-04. These live
checks were performed by the user, not by automated tests.

## Phase 5 — implemented, 2026-10-04

- Qt-independent immutable environment items report severity, versions, tool
  locations and repair hints. Reuse the offline impersonation capability adapter.
  Probe external JS tools with finite timeouts and installed-engine version rules;
  explicitly configure found runtime paths for analysis and downloads. Disable
  remote EJS fetching. Warnings remain nonfatal.
- Startup checks run asynchronously; a non-modal Settings > Engine/Environment
  panel exposes refresh, repair commands, current engine version and diagnostics.
- Latest stable release checks are explicit, HTTPS-only, offline-safe and bounded.
  Confirmed venv updates revalidate official metadata, verify PyPI wheel SHA-256,
  and invoke current-interpreter pip with argument lists, isolated config, binary
  dependencies, captured redacted output and cancellation. Refuse while downloads
  or analysis are active; pause scheduling and require restart after any attempt.
  Refuse frozen/system updates and releases outside the project dependency range.
- QSettings stores versioned first-run disclaimer acceptance. Rejection exits;
  Help/About shows versions, MIT license, repository and disclaimer.
- Open logs folder and Copy diagnostics exclude sensitive material from shared
  reports. Logs redact user paths and retain traceback basenames. Typed errors
  explain network/login/age/geo/quality/FFmpeg recovery without bypassing access.
- Offline pytest-qt tests mock environment/updater/network/pip. Ruff and sequential
  coverage checks pass; manual user verification is listed in NOTES.md.

Stop at the Phase 5 gate. Phase 6 requires a new user continue.

## Remaining roadmap (not Phase 5 work)

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
FormatChoice accepts any positive integer video height ceiling so desktop choices
can match real metadata; CLI retains preset choices. Unknown metadata remains unknown. See DECISIONS.md for detailed path, playlist,
compatibility, logging and cancellation constraints; NOTES.md records evidence.

## Phase-gate checklist

Update README.md together with SPEC.md, DECISIONS.md and NOTES.md before every
final phase commit; describe implemented features only. Run lint/format and
sequential offline pytest with coverage and --basetemp=.pytest_tmp, commit locally,
report the gate and stop for continue.
