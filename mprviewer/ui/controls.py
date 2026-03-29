"""
mprviewer.ui.controls
~~~~~~~~~~~~~~~~~~~~~
ControlPanel — the left sidebar widget.

Emits Qt signals upward to MainWindow. Contains no image logic.
All terminology follows radiological convention:
    "Window/Level" not "Brightness/Contrast"
    W = window width  (contrast)
    L = window level  (center/brightness)
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QGroupBox, QFrame, QScrollArea, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal

from mprviewer.ui.theme import ThemeManager

_theme = ThemeManager()

COLORMAPS = ["gray", "viridis", "plasma", "inferno", "magma", "cividis",
             "hot", "bone", "jet"]
VR_PRESETS = ["mri_default", "bone", "angio", "pet"]

PLANES = ["Axial", "Coronal", "Sagittal"]


# ---------------------------------------------------------------------------
# ControlPanel
# ---------------------------------------------------------------------------

class ControlPanel(QWidget):
    """
    Left sidebar — all controls, no image logic.

    Signals:
        load_requested()
        dicom_load_requested()
        play_toggled(bool)          True = start playing
        colormap_changed(str)
        vr_preset_changed(str)
        wl_changed(int, float, float)   plane_index, center, width
        reset_requested()
        theme_toggled()
        vr_visibility_changed(bool)
    """

    load_requested       = pyqtSignal()
    dicom_load_requested = pyqtSignal()
    play_toggled         = pyqtSignal(bool)
    colormap_changed     = pyqtSignal(str)
    vr_preset_changed    = pyqtSignal(str)
    wl_changed           = pyqtSignal(int, float, float)
    reset_requested      = pyqtSignal()
    theme_toggled        = pyqtSignal()
    vr_visibility_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self._playing = False
        self._build()

    # =========================================================================
    # Build
    # =========================================================================

    def _build(self):
        T = _theme.palette()
        self.setStyleSheet(f"background:{T['sidebar']};")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border:none; background:{T['sidebar']}; }}
            QScrollBar:vertical {{ background:transparent; width:4px; }}
            QScrollBar::handle:vertical {{
                background:{T['border_med']}; border-radius:2px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        inner = QWidget()
        inner.setStyleSheet(f"background:{T['sidebar']};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(8)

        # ── Logo / title ──────────────────────────────────────────────────────
        title = QLabel("MPRViewer")
        title.setStyleSheet(
            f"color:{T['accent']}; font-size:16px; font-weight:800; "
            f"background:transparent; padding-bottom:2px;"
        )
        lay.addWidget(title)
        lay.addWidget(_hsep(T))

        # ── Load ──────────────────────────────────────────────────────────────
        self._load_btn  = _btn_primary("Load NIfTI", T)
        self._dicom_btn = _btn_secondary("Load DICOM series", T)
        self._load_btn.setToolTip("Load .nii or .nii.gz file")
        self._dicom_btn.setToolTip("Load a folder of DICOM files")
        lay.addWidget(self._load_btn)
        lay.addWidget(self._dicom_btn)
        lay.addWidget(_hsep(T))

        # ── Playback ──────────────────────────────────────────────────────────
        pb = _section("Cine playback", T)
        self._play_btn = _btn_secondary("▶  Play", T)
        self._play_btn.setToolTip("Animate through axial slices")
        pb.addWidget(self._play_btn)
        lay.addWidget(pb)

        # ── Colormap ──────────────────────────────────────────────────────────
        cm = _section("Colormap", T)
        self._cmap_combo = _combo(COLORMAPS, T)
        self._cmap_combo.setToolTip("Apply colormap to all three planes")
        cm.addWidget(self._cmap_combo)
        lay.addWidget(cm)
        lay.addWidget(_hsep(T))

        # ── Window / Level per plane ──────────────────────────────────────────
        wl_sec = _section("Window / Level", T)
        note = QLabel("W = width (contrast)   L = level (brightness)")
        note.setWordWrap(True)
        note.setStyleSheet(
            f"color:{T['text_ter']}; font-size:10px; background:transparent;"
        )
        wl_sec.addWidget(note)

        self._w_sliders: list[QSlider] = []
        self._l_sliders: list[QSlider] = []

        for i, plane in enumerate(PLANES):
            grp = QGroupBox(plane)
            grp.setStyleSheet(f"""
                QGroupBox {{
                    color:{T['text_sec']}; font-size:11px; font-weight:600;
                    border:1px solid {T['border_med']}; border-radius:5px;
                    margin-top:6px; padding-top:6px;
                    background:{T['card_bg']};
                }}
                QGroupBox::title {{
                    subcontrol-origin:margin; left:8px;
                    color:{T['accent']};
                }}
            """)
            gl = QVBoxLayout(grp)
            gl.setSpacing(4)
            gl.setContentsMargins(8, 8, 8, 8)

            w_row, w_sl = _slider_row("W", 1, 200, 100, T)
            l_row, l_sl = _slider_row("L", 0, 100, 50, T)
            w_sl.setToolTip(
                f"{plane}: Window width — controls contrast range"
            )
            l_sl.setToolTip(
                f"{plane}: Window level — controls brightness centre"
            )
            w_sl.valueChanged.connect(
                lambda _, idx=i: self._emit_wl(idx)
            )
            l_sl.valueChanged.connect(
                lambda _, idx=i: self._emit_wl(idx)
            )

            gl.addLayout(w_row)
            gl.addLayout(l_row)
            wl_sec.addWidget(grp)
            self._w_sliders.append(w_sl)
            self._l_sliders.append(l_sl)

        lay.addWidget(wl_sec)
        lay.addWidget(_hsep(T))

        # ── Volume rendering ──────────────────────────────────────────────────
        vr_sec = _section("Volume rendering", T)
        self._vr_cb = QCheckBox("Show 3D viewport")
        self._vr_cb.setStyleSheet(f"""
            QCheckBox {{
                color:{T['text']}; font-size:12px; background:transparent;
            }}
            QCheckBox::indicator {{
                width:14px; height:14px;
                border:1.5px solid {T['border_med']};
                border-radius:3px; background:{T['surface']};
            }}
            QCheckBox::indicator:checked {{
                background:{T['accent']}; border-color:{T['accent']};
            }}
        """)
        self._vr_cb.setToolTip("Toggle the embedded VTK volume rendering panel")
        vr_sec.addWidget(self._vr_cb)

        self._vr_preset_combo = _combo(VR_PRESETS, T)
        self._vr_preset_combo.setToolTip("Transfer function preset for volume rendering")
        vr_sec.addWidget(QLabel("Preset:").setParent(vr_sec) or _tiny_lbl("Preset:", T))
        vr_sec.addWidget(self._vr_preset_combo)
        lay.addWidget(vr_sec)
        lay.addWidget(_hsep(T))

        # ── Reset + theme ─────────────────────────────────────────────────────
        self._reset_btn = _btn_secondary("↺  Reset view", T)
        self._reset_btn.setToolTip(
            "Reset window/level, crosshairs, and zoom to defaults"
        )
        self._theme_btn = _btn_secondary("", T)
        self._theme_btn.setFixedWidth(36)
        self._theme_btn.setToolTip("Toggle light / dark mode")
        self._update_theme_icon()

        row = QHBoxLayout()
        row.addWidget(self._reset_btn, stretch=1)
        row.addWidget(self._theme_btn)
        rw = QWidget()
        rw.setStyleSheet("background:transparent;")
        rw.setLayout(row)
        lay.addWidget(rw)
        lay.addStretch()

        scroll.setWidget(inner)
        ol = QVBoxLayout(self)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)

        # Wire signals
        self._load_btn.clicked.connect(self.load_requested)
        self._dicom_btn.clicked.connect(self.dicom_load_requested)
        self._play_btn.clicked.connect(self._on_play)
        self._cmap_combo.currentTextChanged.connect(self.colormap_changed)
        self._reset_btn.clicked.connect(self.reset_requested)
        self._theme_btn.clicked.connect(self._on_theme)
        self._vr_cb.toggled.connect(self.vr_visibility_changed)
        self._vr_preset_combo.currentTextChanged.connect(self.vr_preset_changed)

    # =========================================================================
    # Public helpers
    # =========================================================================

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        self._play_btn.setText("⏸  Pause" if playing else "▶  Play")

    def window_level(self, plane_index: int) -> tuple[float, float]:
        """Return (center, width) in [0, 1] for the given plane."""
        w = self._w_sliders[plane_index].value() / 100.0
        l = self._l_sliders[plane_index].value() / 100.0
        return l, w

    def reset_wl(self) -> None:
        """Reset all window/level sliders to defaults."""
        for sl in self._w_sliders:
            sl.blockSignals(True)
            sl.setValue(100)
            sl.blockSignals(False)
        for sl in self._l_sliders:
            sl.blockSignals(True)
            sl.setValue(50)
            sl.blockSignals(False)

    def apply_theme(self) -> None:
        """Rebuild sidebar styles after theme toggle."""
        self._update_theme_icon()
        # Full rebuild requires recreating the widget — simpler to just
        # update the accent-colored elements
        T = _theme.palette()
        self.setStyleSheet(f"background:{T['sidebar']};")

    # =========================================================================
    # Internal
    # =========================================================================

    def _on_play(self) -> None:
        self._playing = not self._playing
        self.set_playing(self._playing)
        self.play_toggled.emit(self._playing)

    def _on_theme(self) -> None:
        self.theme_toggled.emit()
        self._update_theme_icon()

    def _update_theme_icon(self) -> None:
        self._theme_btn.setText("☀" if _theme.is_dark() else "🌙")

    def _emit_wl(self, idx: int) -> None:
        center, width = self.window_level(idx)
        self.wl_changed.emit(idx, center, width)


# ---------------------------------------------------------------------------
# Style helpers (private to this module)
# ---------------------------------------------------------------------------

def _btn_primary(text: str, T: dict) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(30)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{T['accent']}; color:#000;
            border:none; border-radius:6px;
            font-size:12px; font-weight:700; padding:0 12px;
        }}
        QPushButton:hover  {{ background:{T['accent_h']}; }}
        QPushButton:pressed{{ background:{T['accent_l']}; color:{T['text']}; }}
        QPushButton:disabled{{ background:{T['border']}; color:{T['text_ter']}; }}
    """)
    return b


def _btn_secondary(text: str, T: dict) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(30)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{T['surface']}; color:{T['text']};
            border:1px solid {T['border_med']}; border-radius:6px;
            font-size:12px; padding:0 12px;
        }}
        QPushButton:hover  {{ border-color:{T['accent']}; color:{T['accent']}; }}
        QPushButton:pressed{{ background:{T['border']}; }}
        QPushButton:disabled{{ color:{T['text_ter']}; }}
    """)
    return b


def _combo(items: list[str], T: dict) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    cb.setFixedHeight(28)
    cb.setStyleSheet(f"""
        QComboBox {{
            background:{T['surface']}; color:{T['text']};
            border:1px solid {T['border_med']}; border-radius:5px;
            padding:0 8px; font-size:12px;
        }}
        QComboBox:hover {{ border-color:{T['accent']}; }}
        QComboBox::drop-down {{ border:none; width:16px; }}
        QComboBox QAbstractItemView {{
            background:{T['surface']}; color:{T['text']};
            selection-background-color:{T['accent_l']};
            selection-color:{T['accent']};
        }}
    """)
    return cb


def _hsep(T: dict) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{T['border']}; border:none;")
    return f


def _section(title: str, T: dict) -> QGroupBox:
    grp = QGroupBox(title)
    grp.setLayout(QVBoxLayout())
    grp.layout().setContentsMargins(0, 8, 0, 4)
    grp.layout().setSpacing(4)
    grp.setStyleSheet(f"""
        QGroupBox {{
            color:{T['text_sec']}; font-size:11px; font-weight:700;
            border:none; margin-top:8px; padding-top:4px;
            background:transparent;
        }}
        QGroupBox::title {{
            subcontrol-origin:margin; left:0px;
            color:{T['text_sec']};
            text-transform:uppercase; letter-spacing:0.5px;
        }}
    """)
    return grp


def _slider_row(label: str, lo: int, hi: int, val: int,
                T: dict) -> tuple[QHBoxLayout, QSlider]:
    sl = QSlider(Qt.Horizontal)
    sl.setRange(lo, hi)
    sl.setValue(val)
    sl.setFixedHeight(18)
    sl.setStyleSheet(f"""
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
    lbl = QLabel(label)
    lbl.setFixedWidth(14)
    lbl.setStyleSheet(
        f"color:{T['text_sec']}; font-size:11px; background:transparent;"
    )
    val_lbl = QLabel(str(val))
    val_lbl.setFixedWidth(30)
    val_lbl.setStyleSheet(
        f"color:{T['text_ter']}; font-size:10px; background:transparent;"
    )
    val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    sl.valueChanged.connect(lambda v, vl=val_lbl: vl.setText(str(v)))

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(lbl)
    row.addWidget(sl, stretch=1)
    row.addWidget(val_lbl)
    return row, sl


def _tiny_lbl(text: str, T: dict) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{T['text_ter']}; font-size:10px; background:transparent;"
    )
    return lbl