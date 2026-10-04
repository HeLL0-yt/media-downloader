# Contributing

Read [Development](docs/DEVELOPMENT.md), [Architecture](docs/ARCHITECTURE.md) and [AGENTS.md](AGENTS.md). Keep core independent of Qt. Use Windows and CPython 3.14 x64.

## Setup and checks

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest --basetemp=.pytest_tmp --cov=mediagrab.core --cov=mediagrab.desktop --cov-report=term-missing
```

Installation requires internet; default tests are offline. Run sequentially, without the app. Preserve dependency bounds and the 80% branch-coverage threshold unless explicitly authorized to change them. External FFmpeg/Deno are for manual downloads/builds; tests mock external work.

## Changes and commits

- Keep changes focused; add meaningful tests for changed behavior.
- Use small Conventional Commits: `docs: clarify setup`, `fix: preserve cancellation state`, `feat: add capability check`.
- Document user behavior and limitations. At phase gates update README, SPEC, DECISIONS and NOTES, preserving the phase table in docs/PHASES.md.
- Describe the problem, resulting behavior, checks and limitations in the PR template. Follow [Code of conduct](CODE_OF_CONDUCT.md).

## Reports

Use [issue templates](https://github.com/mr-ransaz/MediaGrab/issues/new/choose). Include Windows/Python/app/engine versions, source/frozen mode, sanitized diagnostics, steps, expected and actual behavior. Distinguish manual from automated checks.

Never share cookies, exports, authorization headers, tokens, signed URLs, private media or unreviewed logs/self-check reports. Use a public permitted URL without secrets or describe the platform/restriction instead. Blur account names and paths in screenshots. Report vulnerabilities via [Security](SECURITY.md).
