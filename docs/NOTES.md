# Verification notes

## Current status and contracts

Phases 0–3 are implemented; Phase 4 is authorized by the current request.
The Phase 3 window still uses simulated analysis/downloads and writes no media.
Core is Qt independent. Current contracts are in SPEC.md and DECISIONS.md.

Last completed gate (Phase 3, 2026-10-04):
- Windows CPython 3.14.0, PySide6/Qt 6.11.2, yt-dlp 2026.08.19.
- Ruff lint and format passed (45 files).
- Offline pytest: 500 passed, 1 network test skipped.
- Branch coverage: core 99.14%, desktop 96.49%, combined 98.07%.
- Offscreen entry-point smoke exited 0; no live platform tests were performed.
- Local curl-cffi 0.16.3 exposed 38 impersonation targets during Phase 2.
- Ignored vendor/ffmpeg contains local validation tools, not bundled runtime tools.
  Runtime discovery requires ffmpeg and ffprobe together on an absolute PATH.
- yt-dlp default extra supplies EJS, not an external JavaScript runtime.
  Full runtime startup detection/configuration remains Phase 5.

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
