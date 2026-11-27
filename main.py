"""Backward-compatible launcher: ``python main.py``.

Prefer ``python -m mlenz`` or the installed ``mlenz`` command.
"""

from mlenz.app import main

if __name__ == "__main__":
    raise SystemExit(main())
