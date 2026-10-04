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

Phase 5 user verification, 2026-10-04: first-run disclaimer, About,
Engine/Environment panel, diagnostics, logs and normal MP4/MP3 downloads passed
on Windows. Live updater and missing-Deno/FFmpeg simulation were not run.

## Phase 6 — Windows packaging and tagged release

- Local checkout only; Python 3.14 x64, committed mediagrab.spec, onedir/windowed
  MediaGrab.exe, no UPX. Version comes from pyproject via importlib.metadata;
  copy_metadata supplies the same version in frozen runs and Windows version info.
- Package extractors/plugin support, EJS scripts/data, curl-cffi native libraries,
  certifi CA bundle, Qt platforms/styles/imageformats, themes and generated icon.
  Disclaimer/About text remains in the collected Python modules. Resource helper
  uses package-relative source paths or sys._MEIPASS without consulting cwd.
- Pinned supplier FFmpeg 9.0.2 GPLv3 essentials includes libx264. Official Deno
  2.9.7 MIT is bundled. Fetch scripts compare published and committed SHA-256,
  verify bytes before extraction into ignored vendor/packaging, and copy tools
  next to MediaGrab.exe. Never commit binaries. Full notices/licence text ship.
- Frozen engine pip updating stays refused. UI says to update MediaGrab to get a
  newer engine. Future user engine-directory design is outside Phase 6.
- Non-GUI --self-check logs JSON versions/paths, initializes engine extractors
  and native impersonation, reads certificates/EJS/resources, probes bundled tools
  and evaluates real EJS with Deno offline. --report supports windowed CI output.
- Clean-temp-copy smoke runs with minimal PATH, exercises the real Windows Qt
  window, Environment/disclaimer/About, both themes and image plugins, waits for
  asynchronous offline checks and closes cooperatively with temporary INI settings.
  It never accepts the disclaimer persistently or downloads live media.
- Build isolates native dependency search inside the spec and refuses unrelated
  DLL inputs. In particular it must not substitute Poppler ICU for Windows ICU.
- Keep existing CI. A new v* release workflow on Windows/Python 3.14 runs sequential
  offline gates before build/smoke/zip/SHA-256. Actions use pinned commits; only the
  release job grants contents: write. Tags must match the single project version.
  Publication requires a reviewed complete corresponding-source archive and hash
  for the distributed GPL/LGPL components, uploaded beside the binary zip.
- README covers unsigned-build checks, SmartScreen/antivirus, build/run commands
  and the manual clean-folder/minimal-PATH checklist. Live Blender frozen download
  is optional; Windows 10 acceptance is separate from local Windows 11 evidence.

Phase 6 is complete. Phase 7 was authorized by the user on 2026-10-04.

## Phase 7 — documentation and repository polish, 2026-10-04

Public README covers existing features, source setup, GUI/CLI usage, sites/cookie
limits, architecture, structure, gates, builds, troubleshooting, privacy and use.
Phase history is preserved in PHASES.md and HISTORY.md. ARCHITECTURE, DEVELOPMENT
and BUILDING explain contracts, threading, cancellation, errors, environment,
updater, frozen deployment and trade-offs. Contributor/security/conduct guides,
issue/PR templates and CHANGELOG are included. Metadata is polished without
changing dependencies or coverage. Six labelled SVG screenshot placeholders have
an exact PNG capture checklist; real screenshots remain user-supplied work.
No feature changes, app launch, downloads, push, tag or release in this phase.
Stop at the completed Phase 7 gate; future work needs a new user instruction.

## Future roadmap (not implemented)

macOS, a Telegram bot reusing core, a web app, optional cookies.txt import and
optional staged frozen engine updates with rollback.

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
