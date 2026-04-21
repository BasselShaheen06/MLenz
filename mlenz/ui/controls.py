"""
mlenz.ui.controls
~~~~~~~~~~~~~~~~~~~~~
TopBar controls for the 4-panel grid layout.

All terminology follows radiological convention:
    "Window/Level" not "Brightness/Contrast"
    W = window width  (contrast)
    L = window level  (center/brightness)
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mlenz.ui.theme import ThemeManager

_theme = ThemeManager()

VR_PRESETS = ["mri_default", "bone", "angio", "pet"]


class TopBar(QWidget):
    """Top bar for global actions and rendering toggles."""

    load_requested = pyqtSignal()
    dicom_load_requested = pyqtSignal()
    global_play_toggled = pyqtSignal(bool)
    tour_requested = pyqtSignal()
    reset_requested = pyqtSignal()
    theme_toggled = pyqtSignal()
    vr_visibility_changed = pyqtSignal(bool)
    vr_preset_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        T = _theme.palette()
        self.setFixedHeight(52)
        self.setStyleSheet(f"background:{T['panel']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        title = QLabel("MLenz")
        title.setStyleSheet(
            f"color:{T['accent']}; font-size:15px; font-weight:800;"
            "background: transparent;"
        )
        layout.addWidget(title)

        layout.addWidget(_vsep(T))

        self._load_btn = _btn_primary("Load NIfTI", T)
        self._dicom_btn = _btn_secondary("Load DICOM", T)
        self._load_btn.setToolTip("Load .nii or .nii.gz file")
        self._dicom_btn.setToolTip("Load a single .dcm file")
        layout.addWidget(self._load_btn)
        layout.addWidget(self._dicom_btn)

        self._play_all_btn = _btn_secondary("▶ All", T)
        self._play_all_btn.setCheckable(True)
        self._play_all_btn.setToolTip("Play/Pause cine on all planes")
        self._play_all_btn.toggled.connect(self._on_play_all_toggle)
        layout.addWidget(self._play_all_btn)

        layout.addStretch()

        self._vr_cb = QCheckBox("3D")
        _apply_checkbox(self._vr_cb, T)
        self._vr_cb.setToolTip("Toggle 3D volume view")
        layout.addWidget(self._vr_cb)

        self._vr_preset_combo = _combo(VR_PRESETS, T)
        self._vr_preset_combo.setToolTip("Transfer function preset")
        layout.addWidget(self._vr_preset_combo)

        self._reset_btn = _btn_secondary("Reset", T)
        self._reset_btn.setToolTip("Reset window/level and crosshair")
        layout.addWidget(self._reset_btn)

        self._tour_btn = _btn_secondary("Tour", T)
        self._tour_btn.setToolTip("Guided tour of the interface")
        layout.addWidget(self._tour_btn)

        self._theme_btn = _btn_secondary("", T)
        self._theme_btn.setFixedWidth(36)
        self._theme_btn.setToolTip("Toggle light / dark mode")
        self._update_theme_icon()
        layout.addWidget(self._theme_btn)

        self._load_btn.clicked.connect(self.load_requested)
        self._dicom_btn.clicked.connect(self.dicom_load_requested)
        self._reset_btn.clicked.connect(self.reset_requested)
        self._tour_btn.clicked.connect(self.tour_requested)
        self._theme_btn.clicked.connect(self._on_theme)
        self._vr_cb.toggled.connect(self.vr_visibility_changed)
        self._vr_preset_combo.currentTextChanged.connect(self.vr_preset_changed)

    def set_controls_enabled(self, enabled: bool) -> None:
        for widget in [
            self._load_btn,
            self._dicom_btn,
            self._play_all_btn,
            self._vr_cb,
            self._vr_preset_combo,
            self._reset_btn,
            self._tour_btn,
            self._theme_btn,
        ]:
            widget.setEnabled(enabled)

    def apply_theme(self) -> None:
        self._update_theme_icon()
        T = _theme.palette()
        self.setStyleSheet(f"background:{T['panel']};")
        _apply_btn_primary(self._load_btn, T)
        _apply_btn_secondary(self._dicom_btn, T)
        _apply_btn_secondary(self._play_all_btn, T)
        _apply_btn_secondary(self._reset_btn, T)
        _apply_btn_secondary(self._tour_btn, T)
        _apply_btn_secondary(self._theme_btn, T)
        _apply_combo(self._vr_preset_combo, T)
        _apply_checkbox(self._vr_cb, T)

    def _on_theme(self) -> None:
        self.theme_toggled.emit()
        self._update_theme_icon()

    def _update_theme_icon(self) -> None:
        self._theme_btn.setText("☀" if _theme.is_dark() else "🌙")

    def _on_play_all_toggle(self, checked: bool) -> None:
        self._play_all_btn.setText("⏸ All" if checked else "▶ All")
        self.global_play_toggled.emit(checked)

    def tour_targets(self) -> dict[str, QWidget]:
        return {
            "load_nifti": self._load_btn,
            "load_dicom": self._dicom_btn,
            "play_all": self._play_all_btn,
            "vr_toggle": self._vr_cb,
            "vr_preset": self._vr_preset_combo,
            "reset": self._reset_btn,
            "tour": self._tour_btn,
            "theme": self._theme_btn,
        }



# ---------------------------------------------------------------------------
# Style helpers (private to this module)
# ---------------------------------------------------------------------------

def _btn_primary(text: str, T: dict) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(30)
    _apply_btn_primary(b, T)
    return b


def _apply_btn_primary(button: QPushButton, T: dict) -> None:
    button.setStyleSheet(f"""
        QPushButton {{
            background:{T['accent']}; color:#000;
            border:none; border-radius:6px;
            font-size:12px; font-weight:700; padding:0 12px;
        }}
        QPushButton:hover  {{ background:{T['accent_h']}; }}
        QPushButton:pressed{{ background:{T['accent_l']}; color:{T['text']}; }}
        QPushButton:disabled{{ background:{T['border']}; color:{T['text_ter']}; }}
    """)


def _btn_secondary(text: str, T: dict) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(30)
    _apply_btn_secondary(b, T)
    return b


def _apply_btn_secondary(button: QPushButton, T: dict) -> None:
    button.setStyleSheet(f"""
        QPushButton {{
            background:{T['surface']}; color:{T['text']};
            border:1px solid {T['border_med']}; border-radius:6px;
            font-size:12px; padding:0 12px;
        }}
        QPushButton:hover  {{ border-color:{T['accent']}; color:{T['accent']}; }}
        QPushButton:pressed{{ background:{T['border']}; }}
        QPushButton:disabled{{ color:{T['text_ter']}; }}
    """)


def _combo(items: list[str], T: dict) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    cb.setFixedHeight(28)
    _apply_combo(cb, T)
    return cb


def _apply_combo(combo: QComboBox, T: dict) -> None:
    combo.setStyleSheet(f"""
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


def _apply_checkbox(cb: QCheckBox, T: dict) -> None:
    cb.setStyleSheet(f"""
        QCheckBox {{ color:{T['text']}; font-size:11px; }}
        QCheckBox::indicator {{
            width:14px; height:14px;
            border:1.5px solid {T['border_med']};
            border-radius:3px; background:{T['surface']};
        }}
        QCheckBox::indicator:checked {{
            background:{T['accent']}; border-color:{T['accent']};
        }}
    """)


def _vsep(T: dict) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{T['border']}; border:none;")
    return f