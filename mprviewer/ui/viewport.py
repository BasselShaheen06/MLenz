"""
mprviewer.ui.viewport
~~~~~~~~~~~~~~~~~~~~~
SliceViewport — a reusable Qt widget for displaying one MPR plane.

Each of the three planes (Axial, Coronal, Sagittal) is an instance of
SliceViewport. This eliminates the 3× duplicated canvas/slider/crosshair
code that existed in the original monolithic class.

Signals emitted (connect in MainWindow):
    slice_changed(int)          — slider moved to a new slice index
    crosshair_clicked(float, float, int)  — user clicked in canvas
                                            (x_data, y_data, plane_index)
    scroll_zoomed(str, float, float)      — scroll zoom event
                                            (direction, x_data, y_data)
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal

from mprviewer.ui.theme import ThemeManager

_theme = ThemeManager()


class SliceViewport(QWidget):
    """
    One MPR slice plane: canvas + crosshair lines + slice slider + label.

    Parameters:
        title:       Display name, e.g. "Axial"
        plane_index: 0 = Axial, 1 = Coronal, 2 = Sagittal
    """

    slice_changed    = pyqtSignal(int)
    crosshair_clicked = pyqtSignal(float, float, int)   # x, y, plane
    scroll_zoomed    = pyqtSignal(str, float, float)    # direction, x, y

    def __init__(self, title: str, plane_index: int, parent=None):
        super().__init__(parent)
        self._title       = title
        self._plane_index = plane_index
        self._xlim: tuple | None = None
        self._ylim: tuple | None = None

        T = _theme.palette()
        self.setStyleSheet(f"background:{T['surface']}; border:none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(24)
        title_bar.setStyleSheet(
            f"background:{T['panel']}; border-bottom:1px solid {T['border']};"
        )
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(10, 0, 10, 0)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color:{T['accent']}; font-size:11px; font-weight:700; background:transparent;"
        )
        self._slice_lbl = QLabel("—")
        self._slice_lbl.setStyleSheet(
            f"color:{T['text_sec']}; font-size:10px; background:transparent;"
        )
        tb_lay.addWidget(self._title_lbl)
        tb_lay.addStretch()
        tb_lay.addWidget(self._slice_lbl)
        layout.addWidget(title_bar)

        # ── Matplotlib canvas ─────────────────────────────────────────────────
        self._fig = Figure(facecolor=T["canvas_bg"], tight_layout=True)
        self._ax  = self._fig.add_subplot(111)
        self._ax.set_facecolor(T["canvas_bg"])
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        for sp in self._ax.spines.values():
            sp.set_visible(False)

        self._canvas = FigureCanvas(self._fig)
        self._canvas.setStyleSheet(f"background:{T['canvas_bg']};")
        layout.addWidget(self._canvas, stretch=1)

        # Crosshair lines — created once, updated via set_data()
        self._vline = self._ax.axvline(0, color="#EF5350",
                                       linewidth=1.0, linestyle="--", visible=False)
        self._hline = self._ax.axhline(0, color="#EF5350",
                                       linewidth=1.0, linestyle="--", visible=False)
        self._dot,  = self._ax.plot([], [], "ro", markersize=4, visible=False)

        # ── Slider ────────────────────────────────────────────────────────────
        slider_row = QWidget()
        slider_row.setFixedHeight(28)
        slider_row.setStyleSheet(
            f"background:{T['panel']}; border-top:1px solid {T['border']};"
        )
        sr_lay = QHBoxLayout(slider_row)
        sr_lay.setContentsMargins(8, 4, 8, 4)
        sr_lay.setSpacing(6)

        sr_lay.addWidget(QLabel("◀").setParent(slider_row) or _tiny_lbl("◀", T))
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setValue(0)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height:3px; background:{T['border_med']}; border-radius:2px;
            }}
            QSlider::sub-page:horizontal {{
                background:{T['accent']}; border-radius:2px;
            }}
            QSlider::handle:horizontal {{
                width:12px; height:12px; margin:-5px 0;
                background:{T['surface']}; border-radius:6px;
                border:1.5px solid {T['accent']};
            }}
        """)
        sr_lay.addWidget(self._slider, stretch=1)
        sr_lay.addWidget(_tiny_lbl("▶", T))
        layout.addWidget(slider_row)

        # ── Connect internal signals ──────────────────────────────────────────
        self._slider.valueChanged.connect(self._on_slider)
        self._canvas.mpl_connect("button_press_event", self._on_click)
        self._canvas.mpl_connect("scroll_event",       self._on_scroll)

    # =========================================================================
    # Public API
    # =========================================================================

    def set_range(self, maximum: int) -> None:
        """Set slider range after volume is loaded."""
        self._slider.setRange(0, maximum)

    def set_slice_index(self, index: int) -> None:
        """Set slider position without emitting slice_changed."""
        self._slider.blockSignals(True)
        self._slider.setValue(index)
        self._slider.blockSignals(False)
        self._slice_lbl.setText(f"{index + 1} / {self._slider.maximum() + 1}")

    def display(
        self,
        slice_data: np.ndarray,
        crosshair_x: float,
        crosshair_y: float,
        window_center: float = 0.5,
        window_width: float = 1.0,
        colormap: str = "gray",
    ) -> None:
        """
        Render one slice with window/level and crosshair.

        Args:
            slice_data:     2-D float32 array in [0, 1].
            crosshair_x:    Crosshair column position in data coordinates.
            crosshair_y:    Crosshair row position in data coordinates.
            window_center:  Window level center in [0, 1].
            window_width:   Window width in [0, 1].
            colormap:       Matplotlib colormap name.
        """
        T = _theme.palette()

        # Preserve zoom/pan limits across redraws
        if self._xlim is not None:
            self._ax.set_xlim(self._xlim)
            self._ax.set_ylim(self._ylim)

        self._ax.clear()
        self._ax.set_facecolor(T["canvas_bg"])
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        for sp in self._ax.spines.values():
            sp.set_visible(False)

        # Apply window/level
        lo = window_center - window_width / 2.0
        hi = window_center + window_width / 2.0
        display_data = np.clip((slice_data - lo) / max(hi - lo, 1e-6), 0, 1)

        self._ax.imshow(display_data, cmap=colormap,
                        vmin=0, vmax=1, aspect="equal",
                        interpolation="bilinear")

        # Redraw crosshair lines
        self._vline = self._ax.axvline(
            crosshair_x, color="#EF5350", linewidth=1.0,
            linestyle="--", alpha=0.85,
        )
        self._hline = self._ax.axhline(
            crosshair_y, color="#EF5350", linewidth=1.0,
            linestyle="--", alpha=0.85,
        )
        self._ax.plot(crosshair_x, crosshair_y,
                      "o", color="#EF5350", markersize=4, zorder=5)

        # Restore limits if we had them
        if self._xlim is not None:
            self._ax.set_xlim(self._xlim)
            self._ax.set_ylim(self._ylim)

        self._canvas.draw_idle()

    def apply_theme(self) -> None:
        """Rebuild styles after a theme toggle."""
        T = _theme.palette()
        self.setStyleSheet(f"background:{T['surface']}; border:none;")
        self._fig.set_facecolor(T["canvas_bg"])
        self._ax.set_facecolor(T["canvas_bg"])
        self._canvas.setStyleSheet(f"background:{T['canvas_bg']};")
        self._canvas.draw_idle()

    # =========================================================================
    # Internal event handlers
    # =========================================================================

    def _on_slider(self, value: int) -> None:
        self._slice_lbl.setText(f"{value + 1} / {self._slider.maximum() + 1}")
        self.slice_changed.emit(value)

    def _on_click(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        # Save limits before emitting so the caller can use them
        self._xlim = self._ax.get_xlim()
        self._ylim = self._ax.get_ylim()
        self.crosshair_clicked.emit(
            float(event.xdata), float(event.ydata), self._plane_index
        )

    def _on_scroll(self, event) -> None:
        if event.inaxes != self._ax or event.xdata is None:
            return
        self.scroll_zoomed.emit(
            event.button,
            float(event.xdata),
            float(event.ydata),
        )
        # Apply zoom directly on this viewport
        self._zoom(event.button, event.xdata, event.ydata)

    def _zoom(self, direction: str, x: float, y: float) -> None:
        factor = 1.15 if direction == "up" else (1 / 1.15)
        xlim = self._ax.get_xlim()
        ylim = self._ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        rel_x = (x - xlim[0]) / x_range
        rel_y = (y - ylim[0]) / y_range
        new_xr = x_range / factor
        new_yr = y_range / factor
        self._ax.set_xlim(x - rel_x * new_xr, x - rel_x * new_xr + new_xr)
        self._ax.set_ylim(y - rel_y * new_yr, y - rel_y * new_yr + new_yr)
        self._xlim = self._ax.get_xlim()
        self._ylim = self._ax.get_ylim()
        self._canvas.draw_idle()

    def reset_zoom(self) -> None:
        """Reset zoom/pan to fit the full image."""
        self._xlim = None
        self._ylim = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _tiny_lbl(text: str, T: dict) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{T['text_ter']}; font-size:9px; background:transparent;"
    )
    return lbl