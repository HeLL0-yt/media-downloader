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

## Phase 1 — 2026-10-04

### Immutable core data and explicit quality values

Core requests, format choices, metadata, and progress events use frozen dataclasses
with slots. Download mode and status use string enums. `None` means "best" for a
height ceiling or MP3 bitrate, and unknown for unavailable progress measurements.
Supported height ceilings and bitrates are validated at construction. Metadata
heights use a sorted unique tuple so a worker snapshot cannot be mutated after
delivery. Signed page and thumbnail URLs are excluded from dataclass repr output.

### Strict URL validation without network requests

Validation checks characters before parsing because urllib can discard control
characters. It permits HTTP/HTTPS only and rejects credentials, malformed hosts
and ports, backslashes, internal whitespace, malformed percent escapes, and raw
or percent-decoded control/formatting characters. Internationalized host names and
literal IPv4/IPv6 addresses are supported. Validation does not perform DNS or
restrict local/private hosts; this is a local desktop application.

The optional domain policy accepts bare host names and true subdomains, with a
dot boundary. IP policies match exactly. None means unrestricted, while an empty
policy denies all hosts. A malformed policy fails rather than disabling filtering.
This policy validates the input URL only; redirect/CDN enforcement is not claimed.

### Keep options construction pure

`build_options` receives validated settings, resolved executable paths, and raw
engine hooks. It performs no file creation, network requests, executable discovery,
or callback calls. Each call creates fresh nested configuration. The worker will
call `ensure_output_directory` and `ensure_ffmpeg` separately in Phase 2.

The directory check creates the destination, writes and flushes a temporary probe,
and removes it. This verifies current access; a subsequent permission or disk-space
change can still cause a download failure. The output template has fixed title/ID
fields sanitized by yt-dlp, and literal percent signs in folder names are escaped.
Phase 2 must also check captured final paths against the resolved destination.

### Preserve resolution while preferring compatible codecs

With compatibility enabled, sort fields are `res`, `vcodec:h264`, and `acodec:aac`.
Resolution takes priority; H.264/AAC win among otherwise comparable streams at
that resolution. Disabling the preference uses engine defaults. MP4 merging plus
`FFmpegVideoRemuxer` also covers single combined streams that start in another
container. The verified upstream parameter is spelled `preferedformat`.

A container is not a codec guarantee. Full compatibility requires a Phase 2
post-processing step to verify codecs and re-encode incompatible streams when the
setting is enabled. This preserves the requested resolution at the cost of CPU
time and generation loss. Re-encoding must handle source formats that cannot be
remuxed directly to MP4, and must precede final metadata processing where needed.
This is an explicit Phase 2 requirement, not completed functionality in Phase 1.

### Map MP3 best to VBR quality 0

The best MP3 choice uses `preferredquality="0"`, FFmpeg's highest VBR quality
setting supported by yt-dlp. Explicit bitrates use `"320"`, `"192"`, or `"128"`;
yt-dlp converts values above 10 into kbps encoding arguments. Increasing a target
bitrate does not restore detail absent from the source audio.

### Limit playlist-only URLs in single-video mode

`noplaylist` only resolves ambiguity between a video and its surrounding playlist.
It does not limit an input that identifies only a playlist. Single-video options
therefore also set `playlist_items="1"`. Enabling playlists removes this limit.

### Optional thumbnail failures need local handling

The builder requests `EmbedThumbnail` only for audio when enabled, writes the
thumbnail, and permits its removal after embedding. The engine has no verified
per-postprocessor ignore-failure option. Keeping `ignoreerrors=False` is necessary
to surface real download/conversion errors. In Phase 2 the runner must replace the
thumbnail processor with a best-effort wrapper that reports a safe warning, keeps
the successfully converted MP3, and preserves cancellation. A thumbnail failure
must not cause the entire audio download to fail.

### Require a complete FFmpeg pair in one directory

Discovery checks the executable's directory, `_MEIPASS` when frozen, then absolute
PATH entries. Both executables must be in one directory because `ffmpeg_location`
selects that directory for both tools. Incomplete candidates are skipped. Relative
and empty PATH entries are ignored to avoid loading tools from the current working
directory. Executable checks include access permissions; `ensure_ffmpeg` also runs
both `-version` commands with a five-second timeout each.

Release and Git snapshot version banners are accepted without an invented minimum
version. Required codec capabilities are verified by actual media operations.
The small `core/process.py` helper isolates Windows `CREATE_NO_WINDOW` handling
and uses checked argument-list execution, UTF-8 captured output, and `shell=False`.

### Enforce core coverage now

Windows CI runs the offline suite with branch coverage and the configured 80%
minimum. Real yt-dlp construction, format sorting, and filename preparation are
tested without downloading media, in addition to unit tests for validation,
settings, executable discovery, process safety, and option combinations.
