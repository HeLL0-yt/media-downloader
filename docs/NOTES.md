# Verified upstream notes

## Phase 0 — 2026-10-04

Dependency metadata was checked against PyPI and the local Python 3.14 environment.

| Package | Verified release | Declared range |
| --- | --- | --- |
| PySide6 | 6.11.2 | `>=6.11.2,<6.12` |
| yt-dlp | 2026.8.19 | `>=2026.8.19,<2027`, with `default` extra |
| pytest | 9.1.1 | `>=9.1.1,<10` |
| pytest-qt | 4.5.0 | `>=4.5.0,<5` |
| pytest-cov | 7.1.0 | `>=7.1.0,<8` |
| ruff | 0.16.10 | `>=0.16.10,<0.17` |
| PyInstaller | 6.22.3 | `>=6.22.3,<7` |
| pip-audit | 2.10.1 | `>=2.10.1,<3` |
| setuptools | 84.0.0 | `>=84.0.0,<85` |

Sources: [PySide6](https://pypi.org/project/PySide6/6.11.2/),
[yt-dlp](https://pypi.org/project/yt-dlp/2026.8.19/),
[pytest](https://pypi.org/project/pytest/9.1.1/),
[pytest-qt](https://pypi.org/project/pytest-qt/4.5.0/),
[pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/),
[ruff](https://pypi.org/project/ruff/0.16.10/),
[PyInstaller](https://pypi.org/project/pyinstaller/6.22.3/),
[pip-audit](https://pypi.org/project/pip-audit/2.10.1/),
[setuptools](https://pypi.org/project/setuptools/84.0.0/).

### YouTube JavaScript support

The [yt-dlp 2026.08.19 README](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/README.md#dependencies)
states that full YouTube support requires yt-dlp-ejs and a supported external
JavaScript runtime. Deno is recommended; Node.js, Bun, and QuickJS are also listed.
Only Deno is enabled by default. Merely detecting another runtime does not mean
yt-dlp is configured to use it.

The installed `yt-dlp` distribution metadata confirms that its `default` extra
requires `yt-dlp-ejs==0.8.0`. MediaGrab uses that extra. Phase 5 will verify runtime
availability and versions against the then-installed engine, explicitly configure
supported runtimes, and display missing-component warnings. No runtime download
or runtime execution is added in Phase 0.

FFmpeg and ffprobe are external executables required for merging and audio
conversion. The upstream README explicitly distinguishes these binaries from
Python packages named ffmpeg.

### CI action references

The upstream GitHub API tag references were checked before pinning:

- [actions/checkout v6](https://github.com/actions/checkout/tree/d23441a48e516b6c34aea4fa41551a30e30af803)
- [actions/setup-python v6](https://github.com/actions/setup-python/tree/ece7cb06caefa5fff74198d8649806c4678c61a1)

yt-dlp library option names will be verified against installed source before
implementing the options builder in Phase 1.

### Local Phase 0 validation

Validation used Windows, CPython 3.14.0, and the repository-local `.venv`:

- Editable installation with the `dev` extra succeeded.
- `pip check`: no broken requirements.
- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `pytest` with offscreen Qt: 5 passed.
- `pip wheel . --no-deps --no-build-isolation`: succeeded. Wheel contents include
  the package modules, `py.typed`, and the MIT license, and exclude tests and the
  virtual environment.
- `pip-audit --skip-editable`: no known vulnerabilities found in installed
  dependencies. The editable application itself is excluded from this dependency
  audit; this does not establish that application code is vulnerability-free.

The GitHub-hosted CI run has not been executed locally. Core behavior and GUI
smoke tests will be added in their assigned phases.
