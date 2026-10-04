# Verification notes

## Current status and contracts

Phases 0–4 are implemented; Phase 4 manual Windows gate passed, verified by the user on 2026-10-04, not by automated tests.
The desktop now calls the real core API. Phase 5 has not started.
Core is Qt independent. Current contracts are in SPEC.md and DECISIONS.md.

## Phase 4 evidence — 2026-10-04

- Existing local .venv: Windows CPython 3.14.0, PySide6/Qt 6.11.2,
  yt-dlp 2026.08.19. No new repository, worktree, cloud task or push.
- Installed Qt APIs checked: QSettings backend, QFormLayout.setRowVisible,
  QStyleOptionProgressBar.textAlignment; actual usage exercised offscreen.
- Installed yt-dlp FFmpeg processor source inspected: upstream operations own
  synchronous children. Close waits for return; no thread/process abandonment.
- Real workers tested with mocked get_info/download and mocked thumbnail HTTP.
  Coverage includes progress order/path, cancel/retry/error mapping, limits 1–4,
  canonical metadata URLs, thumbnail limits/failures, QSettings round trip and
  corrupt-value recovery, preferences/theme, rotating/redacted logs and active close.
- Offscreen dark-theme render inspected: aligned form grid, wider centered
  percentage bars and larger queue. Fixture metadata only; no network request.
- Final gate: Ruff check passed; Ruff format --check passed (50 files).
- Sequential offline pytest --basetemp=.pytest_tmp: 543 passed, 1 network test
  skipped in 8.09 seconds. 36 new mocked-core/settings/log tests passed.
- Branch-inclusive coverage: core 99.14%, desktop 95.33%, combined
  97.25%, above the unchanged 80% threshold. Architectural import guard passed.
- Earlier Phase 3 evidence: 500 passed, 1 skipped; core 99.14%, desktop 96.49%.
- curl-cffi 0.16.3 exposed 38 targets in Phase 2. Ignored vendor/ffmpeg binaries
  are local test tools, not packaged tools or part of runtime discovery.
- EJS is installed by yt-dlp default extra; an external JS runtime is still needed
  for full YouTube support. Full startup/runtime configuration remains Phase 5.

## Phase-gate checklist

1. Preserve local user changes and keep all work in this checkout.
2. Implement only the authorized phase; keep GUI networking off the GUI thread.
3. Before the final phase commit update README.md (phases, existing features,
   launch/usage, requirements, troubleshooting), SPEC.md, DECISIONS.md and NOTES.md.
   README must never claim features that do not exist yet.
4. Run Ruff and sequential offline pytest with coverage and --basetemp=.pytest_tmp.
   Never run the app or another pytest instance during a test run.
5. Commit locally, show pwd/recent commits/status and stop for continue.

## Commands

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp --cov=mediagrab.core --cov=mediagrab.desktop --cov-report=term-missing
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m mediagrab.desktop.app
```

Default tests skip network integration. Earlier explicit Blender MP4/MP3 network
and local synthetic conversion checks passed; these do not verify current
YouTube/TikTok/Instagram desktop behavior or account-dependent URLs.

## Historical records

Full older per-phase evidence and installed-source references are preserved in
[HISTORY.md](HISTORY.md). Historical pending-phase wording is superseded above.

## Phase 4 manual gate — passed, 2026-10-04

The user manually verified the Windows desktop gate: YouTube, TikTok and
Instagram 1080p MP4 and MP3 downloads from the window, cancellation mid-download,
invalid URL, no internet and close during download all worked. This evidence was
reported by the user; these live platform checks were not automated tests.
