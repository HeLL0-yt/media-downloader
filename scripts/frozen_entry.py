"""PyInstaller entry point, kept independent of invocation directory."""

import sys

if "--self-check" in sys.argv or "--smoke-test" in sys.argv:
    from mediagrab.self_check import main

    raise SystemExit(main(sys.argv[1:]))

from mediagrab.desktop.app import main

raise SystemExit(main())
