"""
mprviewer.ui.main_window
~~~~~~~~~~~~~~~~~~~~~~~~
MainWindow — top-level Qt window that wires together:
    ControlPanel  (left sidebar)
    SliceViewport × 3  (Axial, Coronal, Sagittal)
    VTK QVTKRenderWindowInteractor  (embedded volume rendering, 4th panel)

Crosshair synchronisation logic lives here because it touches all three
viewports and needs knowledge of the volume shape.

Cine playback timer also lives here for the same reason.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QStatusBar, QLabel, QSplitter, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, QSettings

try:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    _VTK_QT_AVAILABLE = True
except ImportError:
    _VTK_QT_AVAILABLE = False

from mprviewer.core.loader import guess_loader, load_dicom_series
from mprviewer.core.renderer import VolumeRenderer
from mprviewer.ui.controls import ControlPanel
from mprviewer.ui.viewport import SliceViewport
from mprviewer.ui.theme import ThemeManager, DARK, LIGHT

_theme = ThemeManager()

# Plane indices
AXIAL    = 0
CORONAL  = 1
SAGITTAL = 2


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MPRViewer")
        self.setGeometry(80, 80, 1480, 880)

        # Volume state
        self._volume:     np.ndarray | None = None
        self._crosshair = [0, 0, 0]   # [x, y, z] in voxel coordinates
        self._wl: list[tuple[float, float]] = [
            (0.5, 1.0), (0.5, 1.0), (0.5, 1.0)
        ]                              # [(center, width)] per plane
        self._colormap = "gray"

        # VTK renderer
        self._renderer = VolumeRenderer()

        # Cine timer
        self._cine_timer = QTimer()
        self._cine_timer.setInterval(50)   # 20 fps
        self._cine_timer.timeout.connect(self._cine_step)

        self._build_ui()
        self._wire_signals()
        self._apply_theme()

    # =========================================================================
    # Build
    # =========================================================================

    def _build_ui(self):
        T = _theme.palette()

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet(
            f"background:{T['status_bg']}; color:{T['text_sec']}; "
            f"font-size:11px; border-top:1px solid {T['border']};"
        )
        self.setStatusBar(self._status)
        self._status.showMessage("Load a NIfTI or DICOM file to begin")

        # Root widget
        root = QWidget()
        root.setStyleSheet(f"background:{T['bg']};")
        self.setCentralWidget(root)
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Sidebar
        self._controls = ControlPanel()
        root_lay.addWidget(self._controls)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background:{T['border']}; border:none;")
        root_lay.addWidget(sep)

        # Viewport area
        vp_area = QWidget()
        vp_area.setStyleSheet(f"background:{T['bg']};")
        vp_lay = QVBoxLayout(vp_area)
        vp_lay.setContentsMargins(0, 0, 0, 0)
        vp_lay.setSpacing(0)
        root_lay.addWidget(vp_area, stretch=1)

        # 2×2 grid: [Axial | Sagittal] / [Coronal | VTK]
        self._grid = QGridLayout()
        self._grid.setSpacing(2)
        self._grid.setContentsMargins(4, 4, 4, 4)

        self._vp: list[SliceViewport] = [
            SliceViewport("Axial",    AXIAL),
            SliceViewport("Coronal",  CORONAL),
            SliceViewport("Sagittal", SAGITTAL),
        ]
        self._grid.addWidget(self._vp[AXIAL],    0, 0)
        self._grid.addWidget(self._vp[SAGITTAL], 0, 1)
        self._grid.addWidget(self._vp[CORONAL],  1, 0)

        # VTK panel (4th cell)
        self._vtk_container = QWidget()
        self._vtk_container.setStyleSheet("background:#000000;")
        vtk_lay = QVBoxLayout(self._vtk_container)
        vtk_lay.setContentsMargins(0, 0, 0, 0)

        # Title bar for VTK panel
        vtk_bar = QWidget()
        vtk_bar.setFixedHeight(24)
        vtk_bar.setStyleSheet(
            f"background:{T['panel']}; border-bottom:1px solid {T['border']};"
        )
        vtk_bar_lay = QHBoxLayout(vtk_bar)
        vtk_bar_lay.setContentsMargins(10, 0, 10, 0)
        vtk_lbl = QLabel("3D Volume")
        vtk_lbl.setStyleSheet(
            f"color:{T['accent']}; font-size:11px; font-weight:700; background:transparent;"
        )
        vtk_bar_lay.addWidget(vtk_lbl)
        vtk_lay.addWidget(vtk_bar)

        # Embed QVTKRenderWindowInteractor if available
        if _VTK_QT_AVAILABLE:
            self._vtk_widget = QVTKRenderWindowInteractor(self._vtk_container)
            self._vtk_widget.GetRenderWindow().AddRenderer(
                self._renderer.vtk_renderer
            )
            import vtk
            style = vtk.vtkInteractorStyleTrackballCamera()
            self._vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(
                style
            )
            vtk_lay.addWidget(self._vtk_widget, stretch=1)
        else:
            placeholder = QLabel(
                "VTK Qt integration unavailable.\n"
                "Install vtkmodules with Qt support."
            )
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(
                f"color:{T['text_sec']}; background:#000; font-size:12px;"
            )
            self._vtk_widget = None
            vtk_lay.addWidget(placeholder)

        self._grid.addWidget(self._vtk_container, 1, 1)
        self._grid.setRowStretch(0, 1)
        self._grid.setRowStretch(1, 1)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)

        # Hide VTK panel by default — shown when checkbox is ticked
        self._vtk_container.setVisible(False)
        # Show 3rd viewport (coronal) full-width when VTK hidden
        self._grid.setColumnStretch(1, 1)

        vp_lay.addLayout(self._grid, stretch=1)

    # =========================================================================
    # Signal wiring
    # =========================================================================

    def _wire_signals(self):
        c = self._controls

        c.load_requested.connect(self._load_nifti)
        c.dicom_load_requested.connect(self._load_dicom)
        c.play_toggled.connect(self._on_play_toggled)
        c.colormap_changed.connect(self._on_colormap_changed)
        c.wl_changed.connect(self._on_wl_changed)
        c.reset_requested.connect(self._reset)
        c.theme_toggled.connect(self._toggle_theme)
        c.vr_visibility_changed.connect(self._on_vr_visibility)
        c.vr_preset_changed.connect(self._on_vr_preset)

        for vp in self._vp:
            vp.slice_changed.connect(self._on_slice_changed)
            vp.crosshair_clicked.connect(self._on_crosshair_clicked)

    # =========================================================================
    # Load
    # =========================================================================

    def _load_nifti(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Open NIfTI file", "",
            "NIfTI files (*.nii *.nii.gz);;All files (*)",
        )
        if not path:
            return
        self._status.showMessage(f"Loading {Path(path).name} …")
        try:
            self._volume = guess_loader(path)
            self._on_volume_loaded(Path(path).name)
        except Exception as exc:
            self._status.showMessage(f"Error: {exc}")

    def _load_dicom(self):
        from PyQt5.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, "Select DICOM folder"
        )
        if not directory:
            return
        self._status.showMessage(f"Loading DICOM series from {directory} …")
        try:
            self._volume = load_dicom_series(directory)
            self._on_volume_loaded(Path(directory).name)
        except Exception as exc:
            self._status.showMessage(f"Error: {exc}")

    def _on_volume_loaded(self, name: str):
        vol = self._volume
        z, y, x = vol.shape

        # Set slider ranges
        self._vp[AXIAL].set_range(z - 1)
        self._vp[CORONAL].set_range(y - 1)
        self._vp[SAGITTAL].set_range(x - 1)

        # Centre crosshairs
        self._crosshair = [x // 2, y // 2, z // 2]

        # Sync sliders silently
        self._vp[AXIAL].set_slice_index(self._crosshair[2])
        self._vp[CORONAL].set_slice_index(self._crosshair[1])
        self._vp[SAGITTAL].set_slice_index(self._crosshair[0])

        # Load into VTK renderer
        self._renderer.set_volume(vol)
        if self._vtk_widget is not None:
            self._vtk_widget.GetRenderWindow().Render()

        self._update_all()
        self._status.showMessage(
            f"Loaded '{name}'  —  {x} × {y} × {z} voxels"
        )

    # =========================================================================
    # Slice updates
    # =========================================================================

    def _on_slice_changed(self, value: int):
        """Slider moved on one of the viewports."""
        sender = self.sender()
        if sender is self._vp[AXIAL]:
            self._crosshair[2] = value
        elif sender is self._vp[CORONAL]:
            self._crosshair[1] = value
        elif sender is self._vp[SAGITTAL]:
            self._crosshair[0] = value
        self._update_all()

    def _on_crosshair_clicked(self, x: float, y: float, plane: int):
        """User clicked in a viewport canvas — update crosshair position."""
        if self._volume is None:
            return
        vol = self._volume
        z, vy, vx = vol.shape

        if plane == AXIAL:
            self._crosshair[0] = int(np.clip(x, 0, vx - 1))
            self._crosshair[1] = int(np.clip(y, 0, vy - 1))
        elif plane == CORONAL:
            self._crosshair[0] = int(np.clip(x, 0, vx - 1))
            self._crosshair[2] = int(np.clip(
                z - 1 - y, 0, z - 1
            ))
        elif plane == SAGITTAL:
            self._crosshair[1] = int(np.clip(x, 0, vy - 1))
            self._crosshair[2] = int(np.clip(
                z - 1 - y, 0, z - 1
            ))

        # Sync sliders
        self._vp[AXIAL].set_slice_index(self._crosshair[2])
        self._vp[CORONAL].set_slice_index(self._crosshair[1])
        self._vp[SAGITTAL].set_slice_index(self._crosshair[0])

        self._update_all()
        cx, cy, cz = self._crosshair
        self._status.showMessage(
            f"Crosshair  x={cx}  y={cy}  z={cz}"
        )

    def _update_all(self):
        if self._volume is None:
            return
        vol = self._volume
        cx, cy, cz = self._crosshair
        z, vy, vx = vol.shape

        # Axial: slice along Z, crosshair at (cx, cy)
        axial_slice = vol[cz, :, :]
        l, w = self._wl[AXIAL]
        self._vp[AXIAL].display(
            axial_slice, cx, cy,
            window_center=l, window_width=w,
            colormap=self._colormap,
        )

        # Coronal: slice along Y, flip for anatomical orientation
        coronal_slice = np.flipud(vol[:, cy, :])
        l, w = self._wl[CORONAL]
        self._vp[CORONAL].display(
            coronal_slice, cx, z - 1 - cz,
            window_center=l, window_width=w,
            colormap=self._colormap,
        )

        # Sagittal: slice along X, flip for anatomical orientation
        sagittal_slice = np.flipud(vol[:, :, cx])
        l, w = self._wl[SAGITTAL]
        self._vp[SAGITTAL].display(
            sagittal_slice, cy, z - 1 - cz,
            window_center=l, window_width=w,
            colormap=self._colormap,
        )

    # =========================================================================
    # Controls
    # =========================================================================

    def _on_colormap_changed(self, name: str):
        self._colormap = name
        self._update_all()

    def _on_wl_changed(self, idx: int, center: float, width: float):
        self._wl[idx] = (center, width)
        self._update_all()

    def _on_play_toggled(self, playing: bool):
        if playing:
            self._cine_timer.start()
        else:
            self._cine_timer.stop()

    def _cine_step(self):
        if self._volume is None:
            return
        z = self._volume.shape[0]
        next_z = (self._crosshair[2] + 1) % z
        self._crosshair[2] = next_z
        self._vp[AXIAL].set_slice_index(next_z)
        self._update_all()

    def _on_vr_visibility(self, visible: bool):
        self._vtk_container.setVisible(visible)
        if visible and self._vtk_widget is not None:
            self._vtk_widget.GetRenderWindow().Render()
            self._renderer.reset_camera()

    def _on_vr_preset(self, name: str):
        try:
            self._renderer.set_preset(name)
            if self._vtk_widget is not None:
                self._vtk_widget.GetRenderWindow().Render()
        except KeyError:
            pass

    def _reset(self):
        if self._volume is None:
            return
        z, y, x = self._volume.shape
        self._crosshair = [x // 2, y // 2, z // 2]
        self._vp[AXIAL].set_slice_index(self._crosshair[2])
        self._vp[CORONAL].set_slice_index(self._crosshair[1])
        self._vp[SAGITTAL].set_slice_index(self._crosshair[0])
        for vp in self._vp:
            vp.reset_zoom()
        self._controls.reset_wl()
        self._wl = [(0.5, 1.0), (0.5, 1.0), (0.5, 1.0)]
        self._update_all()
        self._status.showMessage("View reset to default")

    # =========================================================================
    # Keyboard panning
    # =========================================================================

    def keyPressEvent(self, event):
        step = 10
        key  = event.key()
        if key == Qt.Key_Left:
            self._pan_focused(-step, 0)
        elif key == Qt.Key_Right:
            self._pan_focused(step, 0)
        elif key == Qt.Key_Up:
            self._pan_focused(0, -step)
        elif key == Qt.Key_Down:
            self._pan_focused(0, step)

    def _pan_focused(self, dx: int, dy: int):
        """Pan whichever viewport the mouse is over."""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QCursor
        widget_under = QApplication.widgetAt(QCursor.pos())
        for vp in self._vp:
            if widget_under is vp or vp.isAncestorOf(widget_under):
                ax = vp._ax
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
                ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
                vp._xlim = ax.get_xlim()
                vp._ylim = ax.get_ylim()
                vp._canvas.draw_idle()
                return

    # =========================================================================
    # Theme
    # =========================================================================

    def _toggle_theme(self):
        _theme.toggle()
        self._apply_theme()

    def _apply_theme(self):
        T = _theme.palette()
        self.setStyleSheet(f"background:{T['bg']};")
        self.centralWidget().setStyleSheet(f"background:{T['bg']};")
        self._status.setStyleSheet(
            f"background:{T['status_bg']}; color:{T['text_sec']}; "
            f"font-size:11px; border-top:1px solid {T['border']};"
        )
        for vp in self._vp:
            vp.apply_theme()
        self._controls.apply_theme()

    # =========================================================================
    # Close
    # =========================================================================

    def closeEvent(self, event):
        self._cine_timer.stop()
        if self._vtk_widget is not None:
            self._vtk_widget.GetRenderWindow().Finalize()
        event.accept()