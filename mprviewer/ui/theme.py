"""
mprviewer.ui.theme
~~~~~~~~~~~~~~~~~~
Dark and light palettes for MPRViewer.

Canvas background is always #000000 in both themes.
Medical images must always be read on a black background —
this is clinical convention, not a style choice.
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
    "canvas_bg":   "#000000",   # always black — never changes
    "crosshair":   "#EF5350",
    "status_bg":   "#091212",
    "overlay_bg":  "rgba(8, 16, 18, 0.82)",
}

LIGHT: dict[str, str] = {
    "bg":          "#F0F4F4",
    "surface":     "#FFFFFF",
    "sidebar":     "#E8F0F0",
    "panel":       "#D8EBEA",
    "accent":      "#00695C",
    "accent_h":    "#00897B",
    "accent_l":    "#B2DFDB",
    "text":        "#0D1B1A",
    "text_sec":    "#3E6B68",
    "text_ter":    "#6A9E9A",
    "border":      "#B2CECE",
    "border_med":  "#9ABCBA",
    "card_bg":     "#E0EFEE",
    "canvas_bg":   "#000000",   # always black — never changes
    "crosshair":   "#EF5350",
    "status_bg":   "#D0E8E6",
    "overlay_bg":  "rgba(220, 240, 238, 0.88)",
}


class ThemeManager:
    """Manages light/dark palette selection with QSettings persistence."""

    def __init__(self):
        settings = QSettings("MPRViewer", "MPRViewer")
        saved = settings.value("theme", None)
        if saved in ("light", "dark"):
            self.current = saved
        else:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                bg = app.palette().color(QPalette.Window)
                lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
                self.current = "dark" if lum < 128 else "light"
            else:
                self.current = "dark"

    def palette(self) -> dict[str, str]:
        self._sync()
        return DARK if self.current == "dark" else LIGHT

    def toggle(self) -> None:
        self.current = "dark" if self.current == "light" else "light"
        QSettings("MPRViewer", "MPRViewer").setValue("theme", self.current)

    def is_dark(self) -> bool:
        self._sync()
        return self.current == "dark"

    def _sync(self) -> None:
        saved = QSettings("MPRViewer", "MPRViewer").value("theme", None)
        if saved in ("light", "dark"):
            self.current = saved