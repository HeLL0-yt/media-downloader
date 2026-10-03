# MediaGrab

MediaGrab is a Python 3.14 desktop application being built for Windows 10/11.
Its planned download engine uses yt-dlp as a library, FFmpeg for media processing,
and PySide6 for the interface.

**Current state: Phase 0 project skeleton. Downloads and the desktop application
are not implemented yet.**

## Planned features

- MP4 video with a maximum height of best, 2160, 1440, 1080, 720, 480, or 360.
- MP3 audio with best, 320, 192, or 128 kbps quality.
- Optional playlists, disabled by default.
- A queue with 1–4 parallel downloads, progress, speed, ETA, cancel, and retry.
- Persistent settings, dark/light themes, and clear download errors.

## Development setup

Use 64-bit CPython 3.14. Run these commands from the repository root in PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
.\.venv\Scripts\python.exe -m pip check
```

The project uses a `src/` layout. Install it before running tests; changing
`PYTHONPATH` is unnecessary. FFmpeg and a JavaScript runtime are external binaries,
not Python packages. Installation and packaging instructions will be added with
their implementation phases.

## Quality checks

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest
```

Tests marked `network` are skipped unless `--run-network` is passed. The network
integration test will be added in Phase 2. GUI tests will use pytest-qt and Qt's
offscreen platform. Core coverage enforcement begins in Phase 1, when executable
core behavior is added:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=mediagrab.core --cov-report=term-missing
.\.venv\Scripts\python.exe -m pip_audit --progress-spinner off --skip-editable
```

GitHub Actions runs lint, formatting checks, offline tests, and an advisory
dependency audit on `windows-latest` with Python 3.14.

## Project structure

```text
.
├── pyproject.toml
├── src/mediagrab/
│   ├── core/                 # No Qt or other GUI imports
│   └── desktop/resources/    # Interface, workers, and themes
├── tests/
├── scripts/                  # Windows build scripts, added in Phase 6
├── docs/
│   ├── DECISIONS.md
│   └── NOTES.md
└── .github/workflows/ci.yml
```

Core progress will use a dataclass callback and cancellation will use
`threading.Event`. The desktop layer will communicate with worker threads through
Qt signals. Windows-specific integration will be isolated from the core.

## Implementation phases

| Phase | Scope | State |
| --- | --- | --- |
| 0 | Package, tooling, tests, Git hygiene, Windows CI | Implemented |
| 1 | Models, errors, validation, FFmpeg discovery, options | Pending |
| 2 | Downloader, error mapping, cancellation, CLI, integration test | Pending |
| 3 | Desktop layout and fake worker | Pending |
| 4 | Real workers, queue, progress, settings | Pending |
| 5 | Environment checks, updater, disclaimer, logging, error UX | Pending |
| 6 | Windows packaging and tagged release workflow | Pending |
| 7 | Full documentation, screenshots, contribution guide, roadmap | Pending |

Each phase ends with lint/test results and a commit. The next phase requires an
explicit `continue`.

## Privacy and security

The planned cookies-from-browser setting will be opt-in and disabled by default.
It allows yt-dlp to read browser session cookies and use the corresponding account
to access a platform. Cookies can grant account access: do not share them, export
them into this repository, or include them in bug reports. MediaGrab will not log
cookie values or full signed URLs.

The implementation will validate HTTP/HTTPS URLs, sanitize output filenames,
check output directory permissions, and avoid shell execution. MediaGrab will
not implement DRM circumvention.

## Responsible use

For personal use only. Respect copyright and the Terms of Service of each
platform. The authors don't encourage downloading content you have no rights to.

## License

MediaGrab source code is licensed under [MIT](LICENSE). Bundled dependencies and
external tools retain their own licenses; distribution notices will be addressed
in the Windows packaging phase.
