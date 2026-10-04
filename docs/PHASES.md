# Implementation phases


| Phase | Scope | State |
| --- | --- | --- |
| 0 | Package, tooling, tests, Git hygiene, Windows CI | Implemented |
| 1 | Models, errors, validation, FFmpeg discovery, options | Implemented |
| 2 | Downloader, error mapping, cancellation, CLI, integration test | Implemented |
| 3 | Desktop layout and fake worker | Implemented |
| 4 | Real workers, queue, progress, settings, local logs and typed errors | Implemented; user manual gate passed |
| 5 | Environment checks, confirmed venv updater, disclaimer/About, diagnostics and error UX | Implemented; automated gate passed; Windows UI, diagnostics, logs and normal downloads user-verified; live updater and missing-tool simulation not run |
| 6 | Windows packaging and tagged release workflow | Implemented; local automated/frozen gate verified; user clean-folder launch/tools/MP4/MP3 verified; Windows 10 and live frozen Blender not run; source-only distribution |
| 7 | Full documentation, screenshots, contribution guide, roadmap | Implemented; labelled placeholders provided; real PNG captures pending from user |

Each phase ends with README/SPEC/DECISIONS/NOTES updates, lint/test results and a commit. The next phase requires an
explicit `continue`.


Earlier decisions and evidence remain in [HISTORY.md](HISTORY.md), [DECISIONS.md](DECISIONS.md) and [NOTES.md](NOTES.md).
