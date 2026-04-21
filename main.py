"""MLenz entry point."""
import sys

from PyQt5.QtWidgets import QApplication

from mprviewer.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MLenz")
    app.setOrganizationName("MLenz")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()