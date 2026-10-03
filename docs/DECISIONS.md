# Design decisions

## Phase 0 — 2026-10-04

### Use the existing repository root

`pyproject.toml`, `src/mediagrab/`, and the supporting directories live at the
repository root. A second `mediagrab/` project directory is unnecessary. The
existing MIT license and copyright attribution are retained.

### Separate packaging and runtime dependencies

Setuptools supplies the PEP 621 build backend. Runtime dependencies are PySide6
and `yt-dlp[default]`. The verified `default` extra includes yt-dlp-ejs, networking
dependencies, and mutagen; it does not install an external JavaScript runtime.
Testing/lint/audit tools live in the `dev` extra. PyInstaller lives in the `build`
extra and is unnecessary for running the application from source.

Dependency declarations have lower and upper version bounds. These are compatible
ranges, not a complete lock of transitive dependencies. Phase 6 must record the
resolved dependency versions used for each distributed Windows artifact.

### Target the requested Python version

The supported interpreter range is `>=3.14,<3.15`. Windows CI uses 64-bit Python
3.14. Adding macOS or another interpreter version requires separate validation.

### Test the installed package

Editable installation exposes the `src/` package. Pytest uses importlib import
mode and does not change `PYTHONPATH`. Smoke tests verify imports and distribution
metadata. A source-level import test enforces the core/GUI boundary. Static import
inspection does not detect every possible dynamic import; core must not use
dynamic imports to bypass that boundary.

Phase 0 tests validate packaging and the architectural boundary. Coverage becomes
an enforced CI check in Phase 1, when core functionality exists. Coverage
configuration already requires at least 80% and includes branch coverage.

### Keep default tests offline

Network tests require the explicit `--run-network` flag, even when selected with
`-m network`. Standard CI does not download platform content. Qt runs with
`QT_QPA_PLATFORM=offscreen` in CI.

### Limit CI permissions

CI has read-only repository permissions and does not persist checkout credentials.
Actions are pinned to commit hashes verified against their upstream `v6` tags.
Dependency auditing is visible but non-blocking, as requested. Lint, formatting,
dependency consistency, and test failures block the job.

### Add executable modules in their assigned phases

The skeleton contains package initializers and resource/script directories.
Downloader, GUI entry points, and build scripts will be added when implemented;
there are no placeholder public functions or nonfunctional launch commands.
