"""
mprviewer.ui.viewport
~~~~~~~~~~~~~~~~~~~~~
SliceViewport — pyqtgraph MPR plane widget with embedded controls.

Bugs fixed vs previous version:
    - Duplicate _on_play method removed (second definition silently dropped first)
    - _live_item was set to None immediately after add — strokes now update
      in-place via setData() which is much faster and correct
    - _emit_play() dead method removed
    - _mini_slider now takes lo/hi/val parameters

Signals:
    slice_changed(int)
    crosshair_moved(float, float, int)
    play_toggled(int, bool)
    cmap_changed(int, str)
    wl_changed(int, float, float)
"""

from __future__ import annotations

import math
import numpy as np
import pyqtgraph as pg
from pyqtgraph import ImageView, InfiniteLine, ScatterPlotItem

from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel,
    QSlider, QPushButton, QVBoxLayout, QWidget,
)

from mprviewer.ui.theme import ThemeManager

_theme = ThemeManager()

pg.setConfigOptions(imageAxisOrder="row-major", antialias=True)

COLORMAPS = ["gray", "viridis", "plasma", "inferno",
             "magma", "cividis", "hot", "bone", "jet"]

CROSSHAIR_COLOR = "#EF5350"
CROSSHAIR_HOVER = "#FF8A80"
ANNOT_COLOR     = "#FFD600"
ANNOT_PEAK_ALPHA = 1.0
ANNOT_GAUSS_SIGMA = 3.0
ANNOT_GAUSS_EXTENT = 4


class SliceViewport(QWidget):

    slice_changed   = pyqtSignal(int)
    crosshair_moved = pyqtSignal(float, float, int)
    play_toggled    = pyqtSignal(int, bool)
    cmap_changed    = pyqtSignal(int, str)
    wl_changed      = pyqtSignal(int, float, float)

    def __init__(self, title: str, plane_index: int, parent=None):
        super().__init__(parent)
        self._title       = title
        self._plane_index = plane_index
        self._blocking    = False
        self._playing     = False
        self._annotating  = False
        self._annot_items: list[pg.PlotDataItem] = []
        self._live_item:   pg.PlotDataItem | None = None
        self._current_stroke: list[QPointF]       = []
        self._slice_annots: dict[int, list[pg.PlotDataItem]] = {}
        self._current_slice = 0

        T = _theme.palette()
        self.setStyleSheet(f"background:{T['surface']}; border:none;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_title_bar())
        root.addWidget(self._build_canvas(), stretch=1)
        root.addWidget(self._build_slider_bar())
        root.addWidget(self._build_control_bar())

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_title_bar(self) -> QWidget:
        T = _theme.palette()
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(22)
        self._title_bar.setStyleSheet(
            f"background:{T['panel']}; border-bottom:1px solid {T['border']};"
        )
        lay = QHBoxLayout(self._title_bar)
        lay.setContentsMargins(8, 0, 8, 0)
        self._title_lbl = QLabel(self._title)
        self._title_lbl.setStyleSheet(
            f"color:{T['accent']}; font-size:11px; font-weight:700; background:transparent;"
        )
        self._slice_lbl = QLabel("—")
        self._slice_lbl.setStyleSheet(
            f"color:{T['text_sec']}; font-size:10px; background:transparent;"
        )
        lay.addWidget(self._title_lbl)
        lay.addStretch()
        lay.addWidget(self._slice_lbl)
        return self._title_bar

    def _build_canvas(self) -> QWidget:
        self._pg_view = ImageView()
        self._pg_view.ui.histogram.hide()
        self._pg_view.ui.roiBtn.hide()
        self._pg_view.ui.menuBtn.hide()
        self._pg_view.ui.roiPlot.hide()
        self._pg_view.setStyleSheet("background:#000000;")
        self._pg_view.getView().setBackgroundColor("#000000")
        self._pg_view.getView().setMenuEnabled(False)
        self._pg_view.getView().setAspectLocked(True)

        pen  = pg.mkPen(CROSSHAIR_COLOR, width=1, style=Qt.DashLine)
        hpen = pg.mkPen(CROSSHAIR_HOVER, width=1.5, style=Qt.DashLine)
        self._vline = InfiniteLine(angle=90, movable=True, pen=pen, hoverPen=hpen)
        self._hline = InfiniteLine(angle=0,  movable=True, pen=pen, hoverPen=hpen)
        self._pg_view.addItem(self._vline)
        self._pg_view.addItem(self._hline)
        self._vline.sigPositionChanged.connect(self._on_drag)
        self._hline.sigPositionChanged.connect(self._on_drag)

        self._dot = ScatterPlotItem(
            size=10,
            pen=pg.mkPen(CROSSHAIR_COLOR, width=1.5),
            brush=pg.mkBrush(None),
            symbol="o",
        )
        self._pg_view.addItem(self._dot)

        # Click-to-jump — ViewBox scene signal
        self._pg_view.getView().scene().sigMouseClicked.connect(
            self._on_canvas_click
        )

        # Annotation mouse intercept
        vb = self._pg_view.getView()
        vb.mousePressEvent   = self._annot_press
        vb.mouseMoveEvent    = self._annot_move
        vb.mouseReleaseEvent = self._annot_release

        return self._pg_view

    def _build_slider_bar(self) -> QWidget:
        T = _theme.palette()
        self._slider_row = QWidget()
        self._slider_row.setFixedHeight(26)
        self._slider_row.setStyleSheet(
            f"background:{T['panel']}; border-top:1px solid {T['border']};"
        )
        lay = QHBoxLayout(self._slider_row)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(4)
        lay.addWidget(_tiny_lbl("◀", T))
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setStyleSheet(_slider_style(T))
        lay.addWidget(self._slider, stretch=1)
        lay.addWidget(_tiny_lbl("▶", T))
        self._slider.valueChanged.connect(self._on_slider)
        return self._slider_row

    def _build_control_bar(self) -> QWidget:
        T = _theme.palette()
        self._ctrl_bar = QWidget()
        self._ctrl_bar.setStyleSheet(
            f"background:{T['card_bg']}; border-top:1px solid {T['border_med']};"
        )
        lay = QVBoxLayout(self._ctrl_bar)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(3)

        # Row 1: ▶  [colormap]  W──  L──
        r1 = QHBoxLayout()
        r1.setSpacing(4)

        self._play_btn = _small_btn("▶", T)
        self._play_btn.setFixedWidth(28)
        self._play_btn.setToolTip("Play/Pause cine through slices")
        self._play_btn.clicked.connect(self._toggle_play)
        r1.addWidget(self._play_btn)

        self._cmap_combo = QComboBox()
        self._cmap_combo.addItems(COLORMAPS)
        self._cmap_combo.setFixedHeight(22)
        self._cmap_combo.setStyleSheet(_combo_style(T))
        self._cmap_combo.setToolTip("Colormap for this plane")
        self._cmap_combo.currentTextChanged.connect(
            lambda name: self.cmap_changed.emit(self._plane_index, name)
        )
        r1.addWidget(self._cmap_combo, stretch=1)

        r1.addWidget(_tiny_lbl("W", T))
        self._w_slider = _mini_slider(1, 200, 100, T)
        self._w_slider.setToolTip("Window width — controls contrast")
        self._w_slider.valueChanged.connect(self._emit_wl)
        r1.addWidget(self._w_slider, stretch=1)

        r1.addWidget(_tiny_lbl("L", T))
        self._l_slider = _mini_slider(0, 100, 50, T)
        self._l_slider.setToolTip("Window level — controls brightness centre")
        self._l_slider.valueChanged.connect(self._emit_wl)
        r1.addWidget(self._l_slider, stretch=1)

        lay.addLayout(r1)

        # Row 2: ✏ Annotate  🗑 Clear  💾 Save  [status]
        r2 = QHBoxLayout()
        r2.setSpacing(4)

        self._annot_btn = _small_btn("✏ Annotate", T)
        self._annot_btn.setCheckable(True)
        self._annot_btn.setToolTip(
            "Toggle annotation mode — click and drag to draw"
        )
        self._annot_btn.toggled.connect(self._on_annot_toggle)
        r2.addWidget(self._annot_btn)

        self._clear_btn = _small_btn("🗑 Clear", T)
        self._clear_btn.setToolTip("Remove all annotations from this plane")
        self._clear_btn.clicked.connect(self.clear_annotations)
        r2.addWidget(self._clear_btn)

        self._save_btn = _small_btn("💾 Save", T)
        self._save_btn.setToolTip("Export viewport (image + annotations) as PNG")
        self._save_btn.clicked.connect(self._save_annotated)
        r2.addWidget(self._save_btn)

        r2.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"color:{T['accent']}; font-size:10px; "
            "background:transparent; font-style:italic;"
        )
        r2.addWidget(self._status_lbl)
        lay.addLayout(r2)
        return self._ctrl_bar

    # ── public API ────────────────────────────────────────────────────────────

    def set_range(self, maximum: int) -> None:
        self._slider.setRange(0, maximum)

    def set_slice_index(self, index: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(index)
        self._slider.blockSignals(False)
        self._slice_lbl.setText(f"{index + 1} / {self._slider.maximum() + 1}")
        self._current_slice = index
        self._refresh_annotations_visibility()

    def set_crosshair(self, x: float, y: float) -> None:
        self._blocking = True
        self._vline.setValue(x)
        self._hline.setValue(y)
        self._dot.setData([x], [y])
        self._blocking = False

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._play_btn.setText("⏸" if playing else "▶")

    def window_level(self) -> tuple[float, float]:
        return self._l_slider.value() / 100.0, self._w_slider.value() / 100.0

    def reset_wl(self) -> None:
        for sl, val in [(self._w_slider, 100), (self._l_slider, 50)]:
            sl.blockSignals(True)
            sl.setValue(val)
            sl.blockSignals(False)

    def display(
        self,
        slice_data: np.ndarray,
        crosshair_x: float,
        crosshair_y: float,
        pixel_spacing: tuple[float, float] = (1.0, 1.0),
        window_center: float = 0.5,
        window_width: float = 1.0,
        colormap: str = "gray",
    ) -> None:
        lo = window_center - window_width / 2.0
        hi = window_center + window_width / 2.0
        data = np.clip((slice_data - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
        self._pg_view.setImage(
            data, autoRange=False, autoLevels=False, levels=(0.0, 1.0)
        )
        try:
            cmap = pg.colormap.get(colormap, source="matplotlib")
            self._pg_view.setColorMap(cmap)
        except Exception:
            self._pg_view.setColorMap(
                pg.colormap.get("gray", source="matplotlib")
            )
        self.set_crosshair(crosshair_x, crosshair_y)
        sx, sy = pixel_spacing
        if sx > 0 and sy > 0 and abs(sx - sy) > 1e-4:
            self._pg_view.getImageItem().resetTransform()
            self._pg_view.getImageItem().scale(sy / sx, 1.0)

    def reset_zoom(self) -> None:
        self._pg_view.autoRange()

    def clear_annotations(self) -> None:
        for items in self._slice_annots.values():
            for item in items:
                    if item.scene() is not None:
                        self._pg_view.removeItem(item)
        if self._live_item is not None:
            try:
                self._pg_view.removeItem(self._live_item)
            except Exception:
                pass
        self._annot_items.clear()
        self._slice_annots.clear()
        self._live_item = None
        self._current_stroke.clear()
        self._status_lbl.setText("")

    def apply_theme(self) -> None:
        T = _theme.palette()
        self.setStyleSheet(f"background:{T['surface']}; border:none;")
        self._title_bar.setStyleSheet(
            f"background:{T['panel']}; border-bottom:1px solid {T['border']};"
        )
        self._title_lbl.setStyleSheet(
            f"color:{T['accent']}; font-size:11px; font-weight:700; background:transparent;"
        )
        self._slice_lbl.setStyleSheet(
            f"color:{T['text_sec']}; font-size:10px; background:transparent;"
        )
        self._slider_row.setStyleSheet(
            f"background:{T['panel']}; border-top:1px solid {T['border']};"
        )
        self._ctrl_bar.setStyleSheet(
            f"background:{T['card_bg']}; border-top:1px solid {T['border_med']};"
        )
        self._slider.setStyleSheet(_slider_style(T))
        self._cmap_combo.setStyleSheet(_combo_style(T))
        for btn in [self._play_btn, self._annot_btn,
                    self._clear_btn, self._save_btn]:
            btn.setStyleSheet(_small_btn_style(T))

    # ── annotation ────────────────────────────────────────────────────────────

    def _on_annot_toggle(self, checked: bool) -> None:
        self._annotating = checked
        vb = self._pg_view.getView()
        if checked:
            self._status_lbl.setText("Drawing mode")
            self._annot_btn.setText("✏ Drawing")
            vb.setCursor(QCursor(Qt.CrossCursor))
            self._vline.setMovable(False)
            self._hline.setMovable(False)
        else:
            self._status_lbl.setText("")
            self._annot_btn.setText("✏ Annotate")
            vb.setCursor(QCursor(Qt.ArrowCursor))
            self._vline.setMovable(True)
            self._hline.setMovable(True)
            self._current_stroke.clear()
            self._live_item = None

    def _annot_press(self, event) -> None:
        if not self._annotating or event.button() != Qt.LeftButton:
            type(self._pg_view.getView()).mousePressEvent(
                self._pg_view.getView(), event
            )
            return
        self._current_slice = self._slider.value()
        self._current_stroke = []
        self._live_item = None
        pos = self._pg_view.getView().mapToView(event.pos())
        self._current_stroke.append(QPointF(pos.x(), pos.y()))
        event.accept()

    def _annot_move(self, event) -> None:
        if not self._annotating or not self._current_stroke:
            type(self._pg_view.getView()).mouseMoveEvent(
                self._pg_view.getView(), event
            )
            return
        pos = self._pg_view.getView().mapToView(event.pos())
        self._current_stroke.append(QPointF(pos.x(), pos.y()))
        self._update_live_stroke()
        event.accept()

    def _annot_release(self, event) -> None:
        if not self._annotating:
            type(self._pg_view.getView()).mouseReleaseEvent(
                self._pg_view.getView(), event
            )
            return
        if len(self._current_stroke) > 1 and self._live_item is not None:
            self._annot_items.append(self._live_item)
            self._slice_annots.setdefault(self._current_slice, []).append(
                self._live_item
            )
        elif self._live_item is not None:
            try:
                self._pg_view.removeItem(self._live_item)
            except Exception:
                pass
        self._live_item = None
        self._current_stroke.clear()
        self._refresh_annotations_visibility()
        event.accept()

    def _update_live_stroke(self) -> None:
        """Update the live stroke in-place — fast, no remove+add."""
        if len(self._current_stroke) < 2:
            return
        xs = [p.x() for p in self._current_stroke]
        ys = [p.y() for p in self._current_stroke]
        if self._live_item is not None:
            self._live_item.setData(xs, ys)   # update in-place
        else:
            self._live_item = pg.PlotDataItem(
                xs, ys, pen=pg.mkPen(ANNOT_COLOR, width=2)
            )
            self._pg_view.addItem(self._live_item)

    def _save_annotated(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, f"Save {self._title} view",
            f"{self._title}_annotated.png",
            "PNG (*.png);;JPEG (*.jpg)",
        )
        if not path:
            return
        pixmap = self._pg_view.grab()
        if pixmap.save(path):
            self._status_lbl.setText("Saved ✓")
        else:
            self._status_lbl.setText("Save failed")

    # ── internal handlers ──────────────────────────────────────────────────────

    def _on_slider(self, value: int) -> None:
        self._slice_lbl.setText(f"{value + 1} / {self._slider.maximum() + 1}")
        self._current_slice = value
        self._refresh_annotations_visibility()
        self.slice_changed.emit(value)

    def _on_drag(self) -> None:
        if self._blocking:
            return
        x = float(self._vline.value())
        y = float(self._hline.value())
        self._dot.setData([x], [y])
        self.crosshair_moved.emit(x, y, self._plane_index)

    def _on_canvas_click(self, event) -> None:
        if self._annotating or event.button() != Qt.LeftButton:
            return
        view_pos = self._pg_view.getView().mapSceneToView(event.scenePos())
        x, y = float(view_pos.x()), float(view_pos.y())
        img = self._pg_view.getImageItem()
        if img.image is None:
            return
        h, w = img.image.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            self._blocking = True
            self._vline.setValue(x)
            self._hline.setValue(y)
            self._dot.setData([x], [y])
            self._blocking = False
            self.crosshair_moved.emit(x, y, self._plane_index)

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        self.set_playing(self._playing)
        self.play_toggled.emit(self._plane_index, self._playing)

    def _emit_wl(self) -> None:
        center, width = self.window_level()
        self.wl_changed.emit(self._plane_index, center, width)

    def _refresh_annotations_visibility(self) -> None:
        for slice_idx, items in self._slice_annots.items():
            for item in items:
                if item.scene() is not None:
                    self._pg_view.removeItem(item)
                distance = abs(slice_idx - self._current_slice)
                if distance > ANNOT_GAUSS_EXTENT:
                    continue
                alpha = ANNOT_PEAK_ALPHA * math.exp(
                    -(distance ** 2) / (2.0 * ANNOT_GAUSS_SIGMA ** 2)
                )
                item.setOpacity(float(alpha))
                self._pg_view.addItem(item)


# ── style helpers ──────────────────────────────────────────────────────────────

def _slider_style(T: dict) -> str:
    return f"""
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
    """

def _combo_style(T: dict) -> str:
    return f"""
        QComboBox {{
            background:{T['surface']}; color:{T['text']};
            border:1px solid {T['border_med']}; border-radius:4px;
            padding:0 6px; font-size:10px;
        }}
        QComboBox:hover {{ border-color:{T['accent']}; }}
        QComboBox::drop-down {{ border:none; width:12px; }}
        QComboBox QAbstractItemView {{
            background:{T['surface']}; color:{T['text']};
            selection-background-color:{T['accent_l']};
        }}
    """

def _small_btn_style(T: dict) -> str:
    return f"""
        QPushButton {{
            background:{T['surface']}; color:{T['text']};
            border:1px solid {T['border_med']}; border-radius:4px;
            font-size:10px; padding:1px 6px;
        }}
        QPushButton:hover {{ border-color:{T['accent']}; color:{T['accent']}; }}
        QPushButton:checked {{
            background:{T['accent_l']}; color:{T['accent']};
            border-color:{T['accent']};
        }}
    """

def _small_btn(text: str, T: dict) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(22)
    b.setStyleSheet(_small_btn_style(T))
    return b

def _mini_slider(lo: int, hi: int, val: int, T: dict) -> QSlider:
    sl = QSlider(Qt.Horizontal)
    sl.setRange(lo, hi)
    sl.setValue(val)
    sl.setFixedHeight(16)
    sl.setStyleSheet(_slider_style(T))
    return sl

def _tiny_lbl(text: str, T: dict) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{T['text_ter']}; font-size:9px; background:transparent;"
    )
    return lbl