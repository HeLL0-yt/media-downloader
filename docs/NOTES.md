# Verification notes

## Current status and contracts

Phases 0–5 are implemented; Phase 4 manual Windows gate passed,
verified by the user on 2026-10-04, not by automated tests.
Phase 5 automated checks pass. On 2026-10-04 the user manually verified the
first-run disclaimer, About, Engine/Environment panel, diagnostics, logs and
normal MP4/MP3 downloads on Windows. The live updater and missing-Deno/FFmpeg
simulation were not run. Phase 6 has not started.
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
  for full YouTube support. Phase 5 now implements startup/runtime configuration.

## Phase 5 evidence — 2026-10-04

- Local checkout only; no cloud/worktree/new repository/push. No real updater,
  pip install, platform download or application launch was performed during tests.
- Installed yt-dlp source inspected: YoutubeDL.py js_runtimes documentation,
  _clean_js_runtimes/_js_runtimes and globals registration; utils/_jsruntime.py
  search rules, banner parsing, minimum versions and normal QuickJS exit code.
  Installed pip configuration.py inspected for isolated/os.devnull config behavior.
- Core environment tests mock package versions, native tool discovery and probes;
  desktop startup checks are mocked throughout the offline suite. Existing offline
  installed-engine impersonation check remains. Update tests mock all HTTPS/pip.
- Tests cover runtime minimums, incomplete FFmpeg pairs, version failures/timeouts,
  package absence, checksum mismatch, insecure redirects, stale/invalid metadata,
  refusal without confirmation/while active/in system or frozen mode, pip failures
  and cancellation, non-modal checks, first-run acceptance/decline/persistence,
  safe diagnostics, About/Help and update close/worker cleanup.
- Fast metadata queued-signal cleanup race reproduced deterministically and fixed.
  Update result delivery is tested before worker cleanup can release scheduling.
- Ruff check passed; Ruff format --check passed (58 files).
- Sequential offline pytest --basetemp=.pytest_tmp: **606 passed, 1 network test
  skipped**, 12.79 seconds. Branch-inclusive coverage: **core 98.72%, desktop
  95.47%, combined 97.07%**, above the unchanged 80% threshold.
- These tests establish offline behavior. The user manually verified the first-run
  disclaimer, About, Engine/Environment panel, diagnostics, logs and normal MP4/MP3
  downloads on Windows on 2026-10-04. The live updater and missing-Deno/FFmpeg
  simulation were not run. This is user-reported evidence, not automated testing.

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

## Phase 5 manual verification checklist

Use only media you have permission to download. Close all existing MediaGrab
windows before launching another copy. Run tests and the app sequentially.

1. Launch `.\.venv\Scripts\python.exe -m mediagrab.desktop.app`. On the first
   launch, choose Exit: the app must exit and ask again next launch. Choose Accept:
   it must persist and not appear next launch. Verify Help > Responsible use
   disclaimer and Help > About (app/Python/Qt/engine versions, MIT, repository).
   Acceptance uses the same Windows QSettings registry namespace across venvs.
2. Open Settings > Engine/Environment. Verify current engine and EJS versions,
   FFmpeg/ffprobe versions and executable locations, supported JS tools and
   impersonation targets. Refresh; the window must remain responsive. Absent
   optional alternatives must not prevent downloading when a supported JS tool
   exists. Warning-only reports must leave downloads available.
3. Verify ordinary permitted MP4/MP3 downloads still work. For error guidance,
   test offline/network failure, a permitted login/age-restricted source using
   browser-cookie opt-in, unavailable quality and missing FFmpeg. Verify safe
   Retry instructions and region restrictions without claims of bypassing them.
4. Select Open logs folder; verify rotation settings remain 2 MiB/four backups.
   Select Copy diagnostics and paste locally: versions/status must be present,
   with no cookie data, signed URLs, output folders or full executable paths.
5. Select Check latest release online, then repeat offline: failure must be clear
   and downloads must remain usable. If the latest release is outside 2026 or
   not yet available as a PyPI wheel, the check must safely refuse it.
6. Verify Update engine requires explicit confirmation (No leaves the venv
   unchanged), refuses with a running download/analysis, and remains responsive.
   Use the disposable venv below for Yes, cancellation or close during updating.
   After any install attempt, downloads remain paused until restart. On failure
   or cancellation, run that disposable venv's pip check and repair as needed.

### Disposable updater environment

These commands create a separate ignored environment, leaving `.venv` packages
unchanged. Installation commands require Internet access and are manual checks,
not part of the automated gate. Do not run the real updater in the development
venv solely to test cancellation.

```powershell
.\.venv\Scripts\python.exe -m venv .\env\phase5-check
.\env\phase5-check\Scripts\python.exe -m pip install --editable .
# Known supported baseline; only this disposable venv is changed:
.\env\phase5-check\Scripts\python.exe -m pip install "yt-dlp[default,curl-cffi]==2026.8.19"
.\env\phase5-check\Scripts\python.exe -m pip check
.\env\phase5-check\Scripts\python.exe -m mediagrab.desktop.app
```

If a newer supported stable release exists, approve an update, restart, and
verify its version in the panel and with this interpreter's `-m yt_dlp --version`.
For cancellation/close testing, use this disposable environment again; afterward:

```powershell
.\env\phase5-check\Scripts\python.exe -m pip check
# Repair this disposable environment after interruption if needed:
.\env\phase5-check\Scripts\python.exe -m pip install --editable .
```

Settings and logs remain shared with the normal app; engine installations are
separate. The mocked updater tests cover success/cancellation/security regardless
of whether an eligible newer live release exists.

### Safely simulate missing Deno and FFmpeg

Use a throwaway PowerShell window and the disposable environment above. Do not
rename/delete installed binaries or change the system/user PATH. First inspect
panel locations: discovery also checks binaries next to Python and JS binaries
in Python's scripts folder, so PATH removal alone does not hide such tools.
A fresh disposable venv has no such external binaries unless manually added.

```powershell
$phase5Python = (Resolve-Path .\env\phase5-check\Scripts\python.exe).Path
$phase5SavedPath = $env:PATH
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    & $phase5Python -m mediagrab.desktop.app
} finally {
    $env:PATH = $phase5SavedPath
}
```

Expect missing JS/YouTube warnings and missing FFmpeg/ffprobe errors. The UI must
stay responsive and show install hints. To isolate missing Deno, include the
verified FFmpeg directory in this temporary PATH. To isolate missing FFmpeg,
include the verified Deno directory instead. Check the panel for Node/Bun/QuickJS:
if another supported runtime is present, the overall YouTube JS check remains OK.
Close the app and shell; subsequent normal launches use the normal PATH.

Stop at Phase 5. Phase 6 requires the user's continue.
