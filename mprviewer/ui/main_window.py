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

from collections import OrderedDict
from pathlib import Path

import numpy as np

from PyQt5.QtCore import Qt, QObject, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

try:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    _VTK_QT_AVAILABLE = True
except ImportError:
    _VTK_QT_AVAILABLE = False

from mprviewer.core.loader import VolumeData, guess_loader, load_dicom_series
from mprviewer.core.renderer import VolumeRenderer
from mprviewer.ui.controls import TopBar
from mprviewer.ui.viewport import SliceViewport
from mprviewer.ui.theme import ThemeManager

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
        self._spacing: tuple[float, float, float] = (1.0, 1.0, 1.0)
        self._crosshair = [0, 0, 0]   # [x, y, z] in voxel coordinates
        self._wl: list[tuple[float, float]] = [
            (0.5, 1.0), (0.5, 1.0), (0.5, 1.0)
        ]                              # [(center, width)] per plane
        self._colormaps: list[str] = ["gray", "gray", "gray"]

        # Render caching + update throttling
        self._slice_cache: OrderedDict[tuple[int, int], np.ndarray] = OrderedDict()
        self._cache_max = 36
        self._prefetch_radius = 2
        self._update_timer = QTimer()
        self._update_timer.setInterval(30)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_all)

        # Background loading state
        self._loading = False
        self._load_thread: QThread | None = None
        self._load_worker: LoadWorker | None = None

        # VTK renderer
        self._renderer = VolumeRenderer()

        # Cine timers (per plane)
        self._cine_timers: list[QTimer] = []
        for plane in (AXIAL, CORONAL, SAGITTAL):
            timer = QTimer()
            timer.setInterval(50)
            timer.timeout.connect(lambda p=plane: self._cine_step(p))
            self._cine_timers.append(timer)

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
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Top bar
        self._top_bar = TopBar()
        root_lay.addWidget(self._top_bar)

        # Content row
        content = QWidget()
        content_lay = QHBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)
        root_lay.addWidget(content, stretch=1)

        # Viewport area
        self._vp_area = QWidget()
        self._vp_area.setStyleSheet(f"background:{T['bg']};")
        vp_lay = QVBoxLayout(self._vp_area)
        vp_lay.setContentsMargins(0, 0, 0, 0)
        vp_lay.setSpacing(0)
        content_lay.addWidget(self._vp_area, stretch=1)

        # Loading overlay
        self._loading_overlay = QWidget(self._vp_area)
        self._loading_overlay.setVisible(False)
        self._loading_overlay.setStyleSheet(
            f"background:{T['overlay_bg']};"
        )
        overlay_lay = QVBoxLayout(self._loading_overlay)
        overlay_lay.setContentsMargins(0, 0, 0, 0)
        overlay_lay.setAlignment(Qt.AlignCenter)
        overlay_label = QLabel("Loading volume…")
        overlay_label.setStyleSheet(
            f"color:{T['text']}; font-size:14px; font-weight:600;"
        )
        overlay_lay.addWidget(overlay_label)

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
            f"color:{T['accent']}; font-size:11px; font-weight:700; "
            "background:transparent;"
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
        self._top_bar.load_requested.connect(self._load_nifti)
        self._top_bar.dicom_load_requested.connect(self._load_dicom)
        self._top_bar.reset_requested.connect(self._reset)
        self._top_bar.theme_toggled.connect(self._toggle_theme)
        self._top_bar.vr_visibility_changed.connect(self._on_vr_visibility)
        self._top_bar.vr_preset_changed.connect(self._on_vr_preset)

        for vp in self._vp:
            vp.slice_changed.connect(self._on_slice_changed)
            vp.crosshair_moved.connect(self._on_crosshair_moved)
            vp.play_toggled.connect(self._on_play_toggled)
            vp.cmap_changed.connect(self._on_colormap_changed)
            vp.wl_changed.connect(self._on_wl_changed)

    # =========================================================================
    # Load
    # =========================================================================

    def _start_load(self, source_name: str, loader_fn, status_message: str):
        if self._loading:
            self._status.showMessage("Loading already in progress")
            return
        self._set_loading_state(True, status_message)

        self._load_thread = QThread()
        self._load_worker = LoadWorker(loader_fn, source_name)
        self._load_worker.moveToThread(self._load_thread)

        self._load_thread.started.connect(self._load_worker.run)
        self._load_worker.finished.connect(self._on_load_finished)
        self._load_worker.failed.connect(self._on_load_failed)
        self._load_worker.finished.connect(self._load_thread.quit)
        self._load_worker.failed.connect(self._load_thread.quit)
        self._load_thread.finished.connect(self._load_worker.deleteLater)
        self._load_thread.finished.connect(self._load_thread.deleteLater)
        self._load_thread.finished.connect(self._on_load_thread_finished)

        self._load_thread.start()

    def _load_nifti(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Open NIfTI file", "",
            "NIfTI files (*.nii *.nii.gz);;All files (*)",
        )
        if not path:
            return
        name = Path(path).name
        self._start_load(
            name,
            lambda: guess_loader(path),
            f"Loading {name} …",
        )

    def _load_dicom(self):
        from PyQt5.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, "Select DICOM folder"
        )
        if not directory:
            return
        name = Path(directory).name
        self._start_load(
            name,
            lambda: load_dicom_series(directory),
            f"Loading DICOM series from {directory} …",
        )

    def _on_load_finished(self, volume: VolumeData, name: str):
        self._volume = volume.data
        self._spacing = volume.spacing
        self._on_volume_loaded(name)
        self._set_loading_state(False, None)

    def _on_load_failed(self, message: str):
        self._set_loading_state(False, f"Error: {message}")

    def _set_loading_state(self, loading: bool, message: str | None):
        self._loading = loading
        if message:
            self._status.showMessage(message)
        self._top_bar.set_controls_enabled(not loading)
        self._loading_overlay.setVisible(loading)
        if loading:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _on_load_thread_finished(self) -> None:
        self._load_thread = None
        self._load_worker = None

    def _on_volume_loaded(self, name: str):
        vol = self._volume
        z, y, x = vol.shape

        self._slice_cache.clear()

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

        self._prefetch_neighbors()

        # Load into VTK renderer
        self._renderer.set_volume(vol, spacing=self._spacing)
        if self._vtk_widget is not None:
            self._vtk_widget.GetRenderWindow().Render()

        self._update_all()
        sx, sy, sz = self._spacing
        self._status.showMessage(
            f"Loaded '{name}'  —  {x} × {y} × {z} voxels  "
            f"| spacing {sx:.2f} × {sy:.2f} × {sz:.2f}"
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
        self._prefetch_neighbors()
        self._schedule_update()

    def _on_crosshair_moved(self, x: float, y: float, plane: int):
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

        self._prefetch_neighbors()
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
        axial_slice = self._get_slice(AXIAL, cz)
        sx, sy, sz = self._spacing
        level, width = self._wl[AXIAL]
        self._vp[AXIAL].display(
            axial_slice, cx, cy,
            pixel_spacing=(sx, sy),
            window_center=level, window_width=width,
            colormap=self._colormaps[AXIAL],
        )

        # Coronal: slice along Y, flip for anatomical orientation
        coronal_slice = self._get_slice(CORONAL, cy)
        level, width = self._wl[CORONAL]
        self._vp[CORONAL].display(
            coronal_slice, cx, z - 1 - cz,
            pixel_spacing=(sx, sz),
            window_center=level, window_width=width,
            colormap=self._colormaps[CORONAL],
        )

        # Sagittal: slice along X, flip for anatomical orientation
        sagittal_slice = self._get_slice(SAGITTAL, cx)
        level, width = self._wl[SAGITTAL]
        self._vp[SAGITTAL].display(
            sagittal_slice, cy, z - 1 - cz,
            pixel_spacing=(sy, sz),
            window_center=level, window_width=width,
            colormap=self._colormaps[SAGITTAL],
        )

    def _schedule_update(self) -> None:
        if not self._update_timer.isActive():
            self._update_timer.start()
        else:
            self._update_timer.start()

    def _get_slice(self, plane: int, index: int) -> np.ndarray:
        key = (plane, index)
        if key in self._slice_cache:
            self._slice_cache.move_to_end(key)
            return self._slice_cache[key]

        vol = self._volume
        if plane == AXIAL:
            data = vol[index, :, :]
        elif plane == CORONAL:
            data = np.flipud(vol[:, index, :])
        else:
            data = np.flipud(vol[:, :, index])

        self._slice_cache[key] = data
        if len(self._slice_cache) > self._cache_max:
            self._slice_cache.popitem(last=False)
        return data

    # =========================================================================
    # Controls
    # =========================================================================

    def _on_colormap_changed(self, plane: int, name: str):
        self._colormaps[plane] = name
        self._schedule_update()

    def _on_wl_changed(self, plane: int, center: float, width: float):
        self._wl[plane] = (center, width)
        self._schedule_update()

    def _on_play_toggled(self, plane: int, playing: bool):
        timer = self._cine_timers[plane]
        if playing:
            timer.start()
        else:
            timer.stop()

    def _cine_step(self, plane: int) -> None:
        if self._volume is None:
            return
        z, y, x = self._volume.shape
        if plane == AXIAL:
            next_idx = (self._crosshair[2] + 1) % z
            self._crosshair[2] = next_idx
            self._vp[AXIAL].set_slice_index(next_idx)
        elif plane == CORONAL:
            next_idx = (self._crosshair[1] + 1) % y
            self._crosshair[1] = next_idx
            self._vp[CORONAL].set_slice_index(next_idx)
        else:
            next_idx = (self._crosshair[0] + 1) % x
            self._crosshair[0] = next_idx
            self._vp[SAGITTAL].set_slice_index(next_idx)

        self._prefetch_neighbors()
        self._schedule_update()

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
        self._slice_cache.clear()
        self._vp[AXIAL].set_slice_index(self._crosshair[2])
        self._vp[CORONAL].set_slice_index(self._crosshair[1])
        self._vp[SAGITTAL].set_slice_index(self._crosshair[0])
        for vp in self._vp:
            vp.reset_zoom()
        self._wl = [(0.5, 1.0), (0.5, 1.0), (0.5, 1.0)]
        self._prefetch_neighbors()
        self._update_all()
        self._status.showMessage("View reset to default")

    def _prefetch_neighbors(self) -> None:
        if self._volume is None:
            return
        z, y, x = self._volume.shape
        cx, cy, cz = self._crosshair
        radius = self._prefetch_radius

        for dz in range(-radius, radius + 1):
            zi = cz + dz
            if 0 <= zi < z:
                self._get_slice(AXIAL, zi)

        for dy in range(-radius, radius + 1):
            yi = cy + dy
            if 0 <= yi < y:
                self._get_slice(CORONAL, yi)

        for dx in range(-radius, radius + 1):
            xi = cx + dx
            if 0 <= xi < x:
                self._get_slice(SAGITTAL, xi)

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
        widget_under = QApplication.widgetAt(QCursor.pos())
        if widget_under is None:
            return
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
        self._loading_overlay.setStyleSheet(f"background:{T['overlay_bg']};")
        self._top_bar.apply_theme()
        for vp in self._vp:
            vp.apply_theme()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._loading_overlay is not None:
            self._loading_overlay.setGeometry(self._vp_area.rect())

    # =========================================================================
    # Close
    # =========================================================================

    def closeEvent(self, event):
        for timer in self._cine_timers:
            timer.stop()
        if self._load_thread is not None:
            try:
                if self._load_thread.isRunning():
                    self._load_thread.quit()
                    self._load_thread.wait(2000)
            except RuntimeError:
                pass
        if self._vtk_widget is not None:
            self._vtk_widget.GetRenderWindow().Finalize()
        event.accept()


class LoadWorker(QObject):
    finished = pyqtSignal(object, str)
    failed = pyqtSignal(str)

    def __init__(self, loader_fn, source_name: str):
        super().__init__()
        self._loader_fn = loader_fn
        self._source_name = source_name

    def run(self) -> None:
        try:
            volume = self._loader_fn()
            self.finished.emit(volume, self._source_name)
        except Exception as exc:
            self.failed.emit(str(exc))