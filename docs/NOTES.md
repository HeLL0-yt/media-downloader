# Verified upstream notes

## Phase 3 gate — complete, 2026-10-04

The desktop prototype is implemented in the current local checkout. Phase 4 has
not started. The historical handoff below describes the previous gate and is
superseded by this section. Stop here until the user says `continue`.

Implemented: app entry point, main window, metadata card/local demo thumbnail,
Video/MP3 controls, quality/bitrate/folder selection, clipboard and URL drag/drop,
queue table and progress delegate, buttons/context menu, fake analysis/download
workers, concurrency/cancel/retry scheduler, in-memory settings and dark QSS.
Version reporting uses core off the GUI thread. No real downloads or analysis
are connected, and the fake worker creates no files. Core remains Qt independent.

### Installed API checks and tests

Qt 6.11.2 QThread.finished/wait(0), connection enums, progress-style enums and
delegate constructors were inspected against the installed PySide6 package.
Offscreen tests exercise actual worker execution and GUI-thread Slots. Qt's
QComboBox converts a stored StrEnum to a string, so mode selection is explicitly
converted back to DownloadMode at the core request boundary. Progress painting
sets State_Horizontal. Context menus use asynchronous popup().

The installed pytest-qt teardown implementation closes and deletes registered
widgets before ordinary fixture cleanup; tests use before_close_func to finish
asynchronous worker shutdown before widget deletion. Tests cover limits 1–4,
FIFO scheduling, pending/active cancellation, fresh-worker retry after injected
failure, signal affinity, GUI timer responsiveness, action buttons/context menu,
engine-version success/failure, stale metadata, clipboard/drop, entry-point
configuration and close during analysis/active/pending work.

### Verification evidence

Windows CPython 3.14.0 and PySide6/Qt 6.11.2 in the existing `.venv`:

- Ruff lint: passed; formatting: **45 files already formatted**.
- Full offline pytest: **500 passed, 1 network test skipped** in 7.74 seconds.
- Branch-inclusive coverage: **99.14% core**, **96.49% desktop**, **98.07% combined**.
  Original core coverage configuration and 80% threshold remain unchanged.
- **25 desktop tests passed**; the core architectural import guard also passed.
- Offscreen module smoke harness ran `mediagrab.desktop.app` as `__main__`, using
  a QApplication subclass that scheduled window close, and exited **0**.
- Offscreen dark-theme render inspected locally. The offscreen plugin has no
  default font directory here; the render harness loaded installed Windows Segoe
  UI for inspection only. No font or executable was added to the application.
- No live platform requests, native interactive Windows session, frozen build or
  GitHub CI run were verified in Phase 3. The status bar correctly reports FFmpeg
  missing when its pair is not discoverable on the process PATH; ignored vendor
  binaries are not added to runtime discovery.

### Reproduce and launch (PowerShell, repository root)

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
New-Item -ItemType Directory -Force .cache/phase3 | Out-Null
.\.venv\Scripts\python.exe -m pytest --basetemp .cache/phase3/gate --cov=mediagrab.core --cov=mediagrab.desktop --cov-report=term-missing --cov-report=xml
git diff --check
Get-Location
git log --oneline -5
git status
```

Launch the native window after clearing the test-only platform override:

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m mediagrab.desktop.app
```

Analyze any valid HTTP/HTTPS URL to display labeled demo information. Add to
queue stages a request; Download adds the selection and starts scheduling;
Start queue starts already staged rows. Cancel/retry/remove operate on simulated
tasks. Open folder opens the requested destination and does not create it.

## Resume here — 2026-10-04

Read `AGENTS.md`, `docs/DECISIONS.md`, this section, and `README.md` before changing
code. Phases **0–2 are complete**; **Phase 3 is pending and requires `continue`**.
The curl-cffi/core environment/CLI follow-up is complete. This handoff adds no GUI
code. Historical phase evidence below records what was verified at each gate,
rather than a list of outstanding implementation work.

At the start of this documentation task, the checkout was clean on `main`, tracking
`origin/main` without an ahead/behind count. Baseline commit:
`3094d25 fix: declare impersonation support and quiet CLI errors`. The handoff
documentation commit follows that baseline. Recheck `git status` and `git log`
in a new session; do not infer current remote state from this dated observation.

### Implemented files and responsibilities

| Location | Implemented behavior |
| --- | --- |
| `pyproject.toml`, `.github/workflows/ci.yml` | Python/dependency bounds, editable src packaging, strict Ruff, Windows offline tests/coverage, advisory pip-audit. |
| `core/models.py`, `errors.py`, `validators.py` | Immutable request/metadata/progress contracts, typed errors, strict HTTP/HTTPS validation/domain policy, writable destination checks. |
| `core/ffmpeg.py`, `process.py`, `options.py` | Complete-pair discovery/version checks, shell-free cancellable subprocesses, pure engine options. |
| `core/downloader.py`, `postprocessors.py` | Lazy metadata analysis, downloads/cancellation, MP4 codec compatibility, optional MP3 artwork, authoritative final-path capture. |
| `core/errors_map.py`, `logging_utils.py` | Conservative friendly error mapping and redacted diagnostics. |
| `core/env_check.py`, `cli.py` | Offline actual impersonation target report, manual download CLI, default traceback suppression with `--verbose` opt-in. |
| `tests/` | Unit/mock/real-engine offline tests, architectural import guard, opt-in Creative Commons MP4/MP3 network integration. |
| `desktop/__init__.py` | Package skeleton only; no runnable desktop application yet. |

No `app.py`, main window, widgets, workers, queue manager, settings implementation,
QSS theme, engine updater, release workflow, build script, or PyInstaller spec is
implemented. Resources/scripts directories are skeletons. Full startup environment
checks, GUI smoke tests, first-run dialog, and rotating file logging remain later
phase work. See DECISIONS for the complete remaining phase gates.

### Environment and dependency baseline

Local validation uses Windows CPython **3.14.0** in repository-local `.venv`,
yt-dlp **2026.08.19**, and PySide6/Qt **6.11.2**. Runtime declarations are:

```text
PySide6>=6.11.2,<6.12
yt-dlp[default,curl-cffi]>=2026.8.19,<2027
curl-cffi>=0.16.0,<0.17
```

The project environment has curl-cffi **0.16.3** and exposed **38** impersonation
targets during the follow-up verification. Installing into another Python does
not install into this `.venv`. Missing targets are a nonfatal core/CLI warning;
the app does not force impersonation globally. The target enumeration API is
private upstream and isolated in `env_check.py`; reverify it after engine upgrades.

The `default` extra supplies yt-dlp-ejs **0.8.0**, not an external JS runtime.
The verified engine docs recommend Deno and enable it by default; other listed
runtimes require configuration. Full YouTube support is not established merely
by installing Python dependencies. Runtime detection/configuration is Phase 5.

### Commands for a new session

Run from the repository root in PowerShell. Create `.venv` with Python 3.14 if it
is absent; installation is unnecessary when the existing environment is intact.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
$env:QT_QPA_PLATFORM = "offscreen"
New-Item -ItemType Directory -Force .cache/handoff | Out-Null
.\.venv\Scripts\python.exe -m pytest --basetemp .cache/handoff/pytest --cov=mediagrab.core --cov-report=term-missing --cov-report=xml
.\.venv\Scripts\python.exe -m yt_dlp --list-impersonate-targets
git diff --check
Get-Location
git log --oneline -3
git status
```

Tests use an explicit project-local base temp because this session's sandbox
denies the default system pytest temp directory. `.cache` and coverage outputs
are ignored. Network tests are skipped unless `--run-network` is passed, including
when selected with `-m network`. With real FFmpeg/ffprobe on PATH, enable them with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_network_download.py --run-network --basetemp .cache/handoff/network
```

The local Codex command wrapper did not preserve a PowerShell PATH addition when
launching Python. For local validation using ignored `vendor/ffmpeg`, set PATH
inside Python before calling pytest:

```powershell
@'
import os
from pathlib import Path
import pytest

os.environ["PATH"] = str(Path("vendor/ffmpeg").resolve()) + os.pathsep + os.environ["PATH"]
raise SystemExit(pytest.main([
    "tests/test_network_download.py", "--run-network",
    "--basetemp", ".cache/handoff/network", "-q",
]))
'@ | .\.venv\Scripts\python.exe -X utf8 -
```

This is a validation environment workaround, not a runtime discovery change.
Create the `.cache/handoff` parent first: pytest creates the base temp itself,
but does not create missing ancestors. The initial handoff rerun failed fixture
setup because that parent was absent; the command above includes its creation.
If pip's system temp directory is also blocked, assign TEMP/TMP to a newly created
directory under `.cache` before installation. Never install project dependencies
into an unrelated interpreter to work around an environment mismatch.

Manual CLI entry point:

```powershell
.\.venv\Scripts\python.exe -m mediagrab.core.cli --help
.\.venv\Scripts\python.exe -m mediagrab.core.cli "https://download.blender.org/peach/trailer/trailer_iphone.m4v" --audio --output-dir .cache/manual
```

Options include `--height`, `--bitrate`, `--playlists`, `--cookies-from-browser`,
`--no-compatibility`, `--no-thumbnail`, and `--verbose`. Height is ignored for audio.
Use Best for direct media with unknown height metadata. Exit codes are 0 success,
1 failure, 130 cancellation, and argparse's 2 for invalid arguments. Tracebacks
are hidden by default; verbose diagnostics remain redacted.

### Verified results and limits

Latest executable-code gate: **475 passed, 1 network test skipped; 99.14% core
coverage including branches**, above the enforced 80% minimum. `env_check.py`
has 100% coverage. Ruff lint/format, `pip check`, and diff whitespace checks passed.
The documentation handoff rerun reproduced **475 passed, 1 skipped, 99.14%** after
creating the base-temp parent; Ruff and `pip check` also passed again. No source
code changed and the network test was not rerun for this documentation-only task.
The explicitly enabled network integration separately passed after curl-cffi was
added; ffprobe confirmed MP4 H.264/AAC and MP3 audio. The dependency audit reported
no known vulnerabilities and excluded the editable application itself.

Real split-stream merging/conversion and optional cover embedding were also
verified with synthetic local media. These checks do not establish every platform
or account-dependent download works. TikTok/Instagram success after manually
installing curl-cffi is user-reported, not an independently repeated platform test.
No GitHub-hosted CI run, GUI launch, or frozen application test was verified here.

Ignored `vendor/ffmpeg/` currently contains `ffmpeg.exe`, `ffprobe.exe`, and the
validation archive. Both executables report Gyan **9.0.2 essentials**; the verified
archive checksum and provenance are recorded below. They are local test tools,
not committed assets or a finished distribution. Temporary `.cache/phase2` fetch
and synthetic-pipeline helpers are not maintained product scripts. A new session
must not depend on ignored files being available on another machine.

### Resume checklist

1. Inspect local status and preserve any user changes; use the current files as
   authority and the historical notes as evidence.
2. Confirm the requested phase. The next authorized phase after `continue` is
   **Phase 3: desktop layout and fake workers**, with no real download integration.
3. Reuse the existing core contracts. Keep network work off the GUI thread, bridge
   callbacks through Signals, and design cooperative worker shutdown before wiring
   real downloads in Phase 4.
4. Run the checks above, record new evidence, commit the phase, and stop. Do not
   present future UI, updater, packaging, or roadmap work as completed.

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

## Phase 2 follow-up: impersonation dependency and CLI diagnostics — 2026-10-04

The installed yt-dlp **2026.08.19** distribution metadata was checked directly.
It declares `Provides-Extra: curl-cffi` and this requirement:

```text
curl-cffi!=0.6.*,!=0.7.*,!=0.8.*,!=0.9.*,<0.17,>=0.5.10;
    (implementation_name == 'cpython') and extra == 'curl-cffi'
```

The installed README also recommends `yt-dlp[default,curl-cffi]` for browser
impersonation. The installed `_curlcffi.py` handler accepts 0.5.10 and 0.10.x
through 0.16.x, and rejects unsupported versions. Sources:

- [yt-dlp impersonation documentation](https://github.com/yt-dlp/yt-dlp#impersonation).
- [Pinned handler source](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/networking/_curlcffi.py).
- [Pinned engine source](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/YoutubeDL.py).
- [curl-cffi 0.16.3 release files](https://pypi.org/project/curl-cffi/0.16.3/#files).

Runtime requirements now include `yt-dlp[default,curl-cffi]>=2026.8.19,<2027` and
the explicit bound `curl-cffi>=0.16.0,<0.17`. The extra identifies the engine
capability; the direct requirement narrows its broad legacy-compatible range to
the verified modern 0.16 series. Upstream's `pin-curl-cffi` extra pins 0.16.0, which
supports this lower bound choice. The upper bound matches the installed handler's
compatibility ceiling; releases 0.17 and later require a fresh compatibility check.

PyPI metadata for 0.16.0 and 0.16.3 was verified before installation. The project
environment installed the `cp310-abi3-win_amd64` wheel for curl-cffi **0.16.3** under
CPython 3.14.0, along with cffi **2.1.1** and pycparser **3.0**. The project `.venv`
initially lacked curl-cffi; a manual install into another interpreter does not
apply to an isolated virtual environment. Source installation now installs this
dependency without a separate manual command.

### Capability check

`core/env_check.py` reports the engine version, sorted unique impersonation target
names, and nonfatal warnings. It initializes an engine without extractors and
enumerates loaded handlers without making HTTP requests or reading browser cookies.
Missing targets produce an actionable reinstall/restart warning; initialization,
native-handler, or API failures produce a safe warning plus a redacted diagnostic.

The installed engine exposes `_get_available_impersonate_targets()` and marks a
public API as a future TODO. That private call is isolated in one adapter; it is
not an invented yt-dlp option. Tests exercise missing/broken handlers and confirm
the installed engine exposes targets while `urlopen` is prohibited. After adding
the declared dependency, the local Windows engine exposes **38 targets** with no
environment warning. The check does not force a target for all downloads.

### Console diagnostics

The CLI emits environment warnings before starting a download. Its console handler
suppresses explicitly tagged core traceback diagnostics unless `--verbose` is
passed. Verbose mode also shows redacted engine debug messages and the capability
summary. Python exception fields are formatted through the core redaction helper;
raw stack source lines and locals are excluded. Traceback records remain available
to other application log handlers, including the later desktop logging setup.
CLI logging configuration is restored after the command returns.

This change stays in Phase 2/core/CLI. No desktop or Phase 3 files are changed.
TikTok/Instagram success after manual curl-cffi installation was reported by the
user; this follow-up does not independently test account-dependent platform URLs.

### Follow-up validation

- Declared dependencies installed successfully in the project `.venv`; `pip check`
  reports no broken requirements.
- `ruff check .` and `ruff format --check .`: passed.
- Offline pytest: **475 passed, 1 network test skipped**, **99.14% core coverage
  including branches**. The new environment module has **100% coverage**.
- Explicit MP4/MP3 Creative Commons network integration: **1 passed** after adding
  curl-cffi, with real ffprobe stream checks.
- Real CLI failure against a deliberately blocked local destination: no traceback
  by default; redacted traceback with `--verbose`; URL query tokens absent in both.
  Terminal failures are printed once instead of duplicating the callback and
  exception messages.
- `pip-audit --skip-editable`: no known vulnerabilities found in installed
  dependencies. The editable application is excluded from this dependency audit.
- Engine's `--list-impersonate-targets`: **38 available targets**.
