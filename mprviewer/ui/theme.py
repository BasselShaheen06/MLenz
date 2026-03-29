"""
mprviewer.ui.theme
~~~~~~~~~~~~~~~~~~
Dark and light theme palettes for MPRViewer.

Default is dark — consistent with ITK-SNAP, 3D Slicer, and OsiriX.
The medical imaging convention of dark backgrounds is not aesthetic;
it reduces eye strain during long reading sessions and makes
pathological bright signal (T2 hyperintensity, gadolinium enhancement)
immediately visible against a near-black background.

Usage:
    from mprviewer.ui.theme import ThemeManager
    tm = ThemeManager()           # detects system preference
    tm.toggle()                   # switch light ↔ dark
    T = tm.palette()              # returns current dict
"""

from __future__ import annotations
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QPalette


DARK: dict[str, str] = {
    "bg":          "#0A1515",
    "surface":     "#0F1E1E",
    "sidebar":     "#0A1515",
    "panel":       "#122020",
    "accent":      "#4DB6AC",
    "accent_h":    "#80CBC4",
    "accent_l":    "#1A3330",
    "text":        "#E0F2F1",
    "text_sec":    "#80CBC4",
    "text_ter":    "#4DB6AC",
    "border":      "#1A3030",
    "border_med":  "#1F3D3D",
    "card_bg":     "#122828",
    "canvas_bg":   "#000000",    # always black for image viewing
    "crosshair":   "#EF5350",    # red — standard clinical crosshair color
    "status_bg":   "#091212",
}

LIGHT: dict[str, str] = {
    "bg":          "#F4F7F7",
    "surface":     "#FFFFFF",
    "sidebar":     "#F4F7F7",
    "panel":       "#F0F7F6",
    "accent":      "#00695C",
    "accent_h":    "#00897B",
    "accent_l":    "#E0F2F1",
    "text":        "#0D1B1A",
    "text_sec":    "#5A7A78",
    "text_ter":    "#9ABCB8",
    "border":      "#E0ECEB",
    "border_med":  "#C4D8D6",
    "card_bg":     "#F0F7F6",
    "canvas_bg":   "#111111",    # keep canvas dark even in light mode
    "crosshair":   "#EF5350",
    "status_bg":   "#E8F0EF",
}


class ThemeManager:
    """Manages light/dark palette selection with QSettings persistence."""

    def __init__(self):
        settings = QSettings("MPRViewer", "MPRViewer")
        saved = settings.value("theme", None)

        if saved in ("light", "dark"):
            self.current = saved
        else:
            # Detect system preference via Qt palette luminance
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                bg = app.palette().color(QPalette.Window)
                lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
                self.current = "dark" if lum < 128 else "light"
            else:
                self.current = "dark"   # default to dark

    def palette(self) -> dict[str, str]:
        return DARK if self.current == "dark" else LIGHT

    def toggle(self) -> None:
        self.current = "dark" if self.current == "light" else "light"
        QSettings("MPRViewer", "MPRViewer").setValue("theme", self.current)

    def is_dark(self) -> bool:
        return self.current == "dark"