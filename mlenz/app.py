"""Application entry point for MLenz.

Kept separate from ``main.py`` so the launcher is installed with the package
and the ``mlenz`` console script works after ``pip install``.
"""

from __future__ import annotations

import sys

from mlenz import __version__


def main() -> int:
    """Start the MLenz desktop application and return the Qt exit code."""
    # Imported lazily so the package can be imported without a display
    # (tests, CLI introspection) and without paying the Qt/VTK import cost.
    from PyQt5.QtWidgets import QApplication

    from mlenz.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("MLenz")
    app.setOrganizationName("MLenz")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
