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

## Phase 2 — 2026-10-04

### Verified engine behavior

The installed yt-dlp **2026.08.19** source was read before using the extraction,
hook, processor, and networking APIs:

- [`YoutubeDL.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/YoutubeDL.py):
  `extract_info(download=False, process=False)`, URL result processing,
  `add_post_processor`, stage ordering, automatic merger ordering, download exit
  codes, final `filepath` updates, thumbnail writes, and `logger` options.
- [`common.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/common.py):
  custom `PostProcessor.run` contract and progress hooks. Hook info copies are
  made before the processor runs, so a finished hook can carry a stale filepath.
  The after-move collector reads the actual updated info instead.
- [`ffmpeg.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/ffmpeg.py):
  merger container selection, audio conversion, metadata, and FFmpeg argument
  handling. Automatic merging precedes registered conversion processors.
- [`embedthumbnail.py`](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/postprocessor/embedthumbnail.py):
  optional artwork conversion, file replacement, and temporary file names.
- [`networking`](https://github.com/yt-dlp/yt-dlp/tree/2026.08.19/yt_dlp/networking):
  public `Request` and `YoutubeDL.urlopen` for optional artwork using the existing
  engine session, rather than a separate unauthenticated HTTP client.
- [`FFmpeg documentation`](https://ffmpeg.org/ffmpeg.html): stream mapping,
  codec copy versus encoding, and output-container handling.

`lazy_playlist` does not mean Analyze can return without walking entries. The
installed `__process_playlist` still enumerates them. Unprocessed extraction plus
bounded URL-result resolution avoids that walk. An offline test registers a real
InfoExtractor with a generator that fails if consumed, proving the boundary.

### Integration media and attribution

The integration test uses the **3,889,885-byte** Big Buck Bunny trailer hosted at
[Blender's download server](https://download.blender.org/peach/trailer/trailer_iphone.m4v).
[Blender's license page](https://peach.blender.org/about/) identifies published
Peach project content as Creative Commons Attribution 3.0 and specifies attribution.
For the trailer and its extracted soundtrack:

**© copyright 2008, Blender Foundation / www.bigbuckbunny.org.**

The test extracts the soundtrack from this trailer, not the separately released
score. It downloads into pytest's temporary directory and commits no media.
This test exercises a generic direct-media extractor; it does not establish that
every platform works or that YouTube's runtime/authentication needs are satisfied.

W3C's Sintel copy was also considered. Its GET request succeeded with urllib,
but the installed engine encountered an anti-bot 403. The integration fixture
therefore uses Blender's trailer, which passed with the engine's default requests.
No anti-bot bypass or forced impersonation was added.

### Local executable verification

[FFmpeg's download page](https://ffmpeg.org/download.html) links third-party
Windows builds, including [Gyan](https://www.gyan.dev/ffmpeg/builds/). The validation
tools were downloaded into the ignored project-local `vendor/ffmpeg/` directory.
They are not committed or packaged in this phase.

The publisher's [essentials checksum endpoint](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256)
resolved to the versioned `ffmpeg-9.0.2-essentials_build.zip.sha256`. The matching
versioned archive was used, rather than independently fetching a moving latest
archive. Its SHA-256 was verified before selectively copying only the two named
executables:

```text
60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba
```

Both binaries report `9.0.2-essentials_build-www.gyan.dev`. The checksum checks
archive integrity against the publisher's HTTPS checksum; it is not an independent
publisher-signature verification. Packaging and dependency-license notices remain
Phase 6 work.

### Local Phase 2 validation

Windows CPython 3.14.0, yt-dlp 2026.08.19, PySide6/Qt 6.11.2:

- `ruff check .` and `ruff format --check .`: passed.
- Offline pytest with branch-inclusive core coverage: **460 passed, 1 network
  test skipped**, **99.08% core coverage**.
- Explicitly enabled network integration: **1 passed**. Real MP4 had H.264/AAC;
  real MP3 had an MP3 audio stream, verified with ffprobe.
- Manual CLI downloaded and returned Blender's final MP4 path.
- Real synthetic VP9/Opus conversion produced H.264/yuv420p/AAC MP4.
- Real separate VP8 and Opus streams went through yt-dlp's automatic merger,
  the compatibility intermediate, codec conversion, metadata, and final path
  collector; ffprobe confirmed H.264/AAC.
- Real optional JPEG embedding produced an MP3 with an attached cover image.
- Native subprocess tests verify both pipes are drained and children are reaped
  on cancellation/timeouts, including a forced-kill fallback.

The sandbox denies pytest's default system temp directory. Local test runs use
`--basetemp .cache/phase2/pytest` within the project; ordinary developer/CI runs
can use the default directory. All binaries, media, temporary test data, and
coverage outputs are ignored. The GitHub-hosted workflow has not been run locally.
