"""Allow ``python -m mlenz``."""

from mlenz.app import main

if __name__ == "__main__":
    raise SystemExit(main())
