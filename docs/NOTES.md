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

## Phase 1 — 2026-10-04

Options were checked against the installed yt-dlp 2026.08.19 distribution before
implementation. The primary references are:

- [`YoutubeDL.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/YoutubeDL.py):
  library option documentation for output templates, filename sanitization,
  retries, concurrent fragments, cookies, transfer/postprocessor hooks, playlist
  handling, format sorting, `final_ext`, and `ffmpeg_location`.
- [`ffmpeg.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/ffmpeg.py):
  `FFmpegExtractAudioPP` quality mapping, MP4 remuxer, and metadata processor.
- [`embedthumbnail.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/embedthumbnail.py):
  thumbnail processing, cleanup, and failure behavior.
- [`__init__.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/__init__.py):
  the upstream CLI-to-library translation confirms processor dictionaries and
  the spelling `preferedformat`.
- [`FormatSorter`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/utils/_utils.py):
  confirms `res`, `vcodec:h264`, and `acodec:aac` as supported sort fields.

`noplaylist` is documented as selecting a single video "if in doubt". The builder
also selects playlist entry 1 when playlists are disabled, so a playlist-only URL
cannot implicitly download all entries.

An MP4 output container does not ensure H.264/AAC playback compatibility. The
upstream remuxer copies streams. The resolution-preserving codec preference is
covered by an offline test using the actual installed engine. Additional codec
verification/conversion is assigned to the Phase 2 download runner.

Upstream `run_pp` re-raises `PostProcessingError` unless global `ignoreerrors` is
True. There is no per-processor flag to make `EmbedThumbnail` optional. Phase 2
therefore requires a local wrapper; the builder retains `ignoreerrors=False`.

Python's [URL parsing security documentation](https://docs.python.org/3.14/library/urllib.parse.html#url-parsing-security)
warns that parsing alone does not validate a URL. Raw controls are checked before
calling `urlsplit`, and URL structure/domain rules are checked explicitly.

No media downloads or real FFmpeg conversions were performed in Phase 1. Tests
use temporary executable placeholders and mocked process results for discovery
and version checks. Real media processing belongs to Phase 2 integration testing.

### Local Phase 1 validation

Windows CPython 3.14.0, yt-dlp 2026.08.19, PySide6/Qt 6.11.2:

- `ruff check .`: passed.
- `ruff format --check .`: passed.
- `pytest --cov=mediagrab.core --cov-report=term-missing --cov-report=xml` with
  offscreen Qt: **314 passed**, **99.12% core coverage including branches**.
- All requested height ceilings, bitrates, and playlist settings are covered.
- Offline real-engine checks cover postprocessor registration, format-selector
  parsing, resolution/codec ordering, filename traversal prevention, and literal
  percent signs in the destination.
- `git diff --check`: passed.

The 80% coverage threshold is now enforced by Windows CI. The GitHub-hosted job
itself has not been run as part of this local phase.
