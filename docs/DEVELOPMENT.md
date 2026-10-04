# Development

Use CPython 3.14 x64 on Windows. Run all commands from the repository root in
PowerShell. The project uses a src layout; install it instead of modifying
PYTHONPATH. Source GUI launch and downloads need external tools as described in
[README](../README.md#quick-start-from-source).

## Commands

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m mediagrab.core.cli --help
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp --cov=mediagrab.core --cov=mediagrab.desktop --cov-report=term-missing
```

For Python edits, apply formatting before checking with
`.\.venv\Scripts\python.exe -m ruff format .`. After tests, remove the offscreen
override before a manual GUI launch:

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m mediagrab.desktop.app
```

Installation is online; quality gates are offline. Do not run the app, builds or
another pytest instance during tests. No feature change is required for a docs
phase. Keep dependency bounds and coverage configuration unchanged.

## Test strategy

- Core unit tests mock engine metadata, hooks, output files and subprocesses;
  validate contracts, errors, cancellation, conversion and redaction.
- Environment/updater tests mock network, packages, tool probes and pip; no real
  installation occurs. Some engine capability checks inspect installed support
  offline.
- Desktop tests use pytest-qt/offscreen and injectable fake workers/core calls;
  validate scheduling, stale results, settings, signal order and shutdown.
- `tests/test_architecture.py` checks core import independence. Packaging tests
  simulate frozen resource/discovery paths; they do not run the GUI app.
- `tests/test_network_download.py` is marked network and skipped by default.
  Explicit integration checks require permission to download the Blender trailer,
  internet and FFmpeg; they fail on missing dependencies rather than silently skip.
- Frozen self-check/native GUI smoke are separate deployment checks after pytest,
  documented in [Building](BUILDING.md). They are not live platform downloads.

Run a targeted offline test while developing, then the full sequential gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_architecture.py --basetemp=.pytest_tmp
```

Optional network check, separate from the offline gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_network_download.py --run-network --basetemp=.pytest_tmp
```

Advisory dependency audit (requires network; not an offline gate):

```powershell
.\.venv\Scripts\python.exe -m pip_audit --progress-spinner off --skip-editable
```

Coverage includes branches and retains an 80% failure threshold. The full local
gate measures core and desktop; existing CI measures core. Test results do not
prove every current platform/account URL works.

## Add a platform check

Here, a platform check means a media-site check such as YouTube/TikTok/Instagram.
For an operating-system change, also validate process flags, discovery, settings,
packaging and native Qt behavior; macOS support is future work.

1. Identify the authorized public-media case and access requirements. Record site,
   engine/runtime versions, format, source/frozen mode and expected result; never
   commit cookie exports, private media or signed URLs.
2. Mock representative metadata and engine failures in existing downloader/error
   tests. Preserve unknown fields and add meaningful cancellation/format checks.
3. If automated live verification is needed, use the existing `network` marker and
   opt-in `--run-network` mechanism. Keep the default suite offline. Clean temporary
   output and assert streams with ffprobe as in the existing network test.
4. Run manual GUI checks separately: permitted MP4/MP3, quality, cancel, failure
   guidance and close. Account-dependent evidence must state cookie opt-in.
5. Record exact checks and omissions in NOTES. Do not infer all URLs work from one
   successful example or treat mocked tests as live evidence.

## Design decisions and trade-offs

Keep pure options separate from discovery I/O, adapt typed core data at the GUI
boundary and retain workers through teardown. Add new front ends against core
contracts instead of importing desktop. Reverify upstream private adapters/error
patterns during engine upgrades. See [Architecture](ARCHITECTURE.md) for costs and
limitations, [Contributing](../CONTRIBUTING.md) for reports/commit style and
[Phases](PHASES.md) for historical scope.
