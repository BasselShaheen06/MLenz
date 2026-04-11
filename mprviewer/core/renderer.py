"""
mprviewer.core.renderer
~~~~~~~~~~~~~~~~~~~~~~~
VTK GPU volume rendering pipeline.

The VolumeRenderer class owns the full VTK pipeline and can be embedded
into a Qt widget via QVTKRenderWindowInteractor, or run standalone.

Transfer function presets cover the most common MRI use cases:
    "mri_default"  — soft tissue, grey-white matter contrast
    "bone"         — high-intensity structures (bone, calcifications)
    "angio"        — vessels and blood (bright on T1 post-contrast)
    "pet"          — hot-metal colormap for PET overlays
"""

from __future__ import annotations

import numpy as np
import vtk
from vtkmodules.util import numpy_support


# ---------------------------------------------------------------------------
# Transfer function presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict] = {
    "mri_default": {
        # (intensity, R, G, B)
        "color": [(0.0, 0.0, 0.0, 0.0),
                  (0.2, 0.3, 0.1, 0.1),
                  (0.5, 0.7, 0.6, 0.6),
                  (1.0, 1.0, 1.0, 1.0)],
        # (intensity, opacity)
        "opacity": [(0.0, 0.0),
                    (0.1, 0.0),
                    (0.3, 0.15),
                    (0.7, 0.4),
                    (1.0, 0.8)],
    },
    "bone": {
        "color": [(0.0, 0.0, 0.0, 0.0),
                  (0.5, 0.4, 0.3, 0.2),
                  (0.8, 0.9, 0.8, 0.7),
                  (1.0, 1.0, 1.0, 0.95)],
        "opacity": [(0.0, 0.0),
                    (0.4, 0.0),
                    (0.6, 0.3),
                    (0.8, 0.7),
                    (1.0, 1.0)],
    },
    "angio": {
        "color": [(0.0, 0.0, 0.0, 0.0),
                  (0.3, 0.5, 0.0, 0.0),
                  (0.6, 1.0, 0.3, 0.0),
                  (1.0, 1.0, 0.9, 0.8)],
        "opacity": [(0.0, 0.0),
                    (0.2, 0.0),
                    (0.4, 0.2),
                    (0.7, 0.6),
                    (1.0, 0.9)],
    },
    "pet": {
        "color": [(0.0, 0.0, 0.0, 0.0),
                  (0.25, 0.0, 0.0, 0.5),
                  (0.5, 0.0, 0.5, 1.0),
                  (0.75, 1.0, 0.5, 0.0),
                  (1.0, 1.0, 1.0, 0.0)],
        "opacity": [(0.0, 0.0),
                    (0.1, 0.0),
                    (0.3, 0.3),
                    (1.0, 0.9)],
    },
}


# ---------------------------------------------------------------------------
# VolumeRenderer
# ---------------------------------------------------------------------------

class VolumeRenderer:
    """
    Manages the VTK GPU ray-cast volume rendering pipeline.

    Usage (embedded in Qt):
        renderer = VolumeRenderer()
        renderer.set_volume(data_array)
        renderer.set_preset("mri_default")
        # Pass renderer.vtk_renderer to a QVTKRenderWindowInteractor

    Usage (standalone window):
        renderer = VolumeRenderer()
        renderer.set_volume(data_array)
        renderer.show_standalone()
    """

    def __init__(self):
        self._data: np.ndarray | None = None
        self._image_data: vtk.vtkImageData | None = None

        # Pipeline components — created once, reused
        self.vtk_renderer = vtk.vtkRenderer()
        self.vtk_renderer.SetBackground(0.05, 0.05, 0.05)

        self._mapper   = vtk.vtkGPUVolumeRayCastMapper()
        self._property = vtk.vtkVolumeProperty()
        self._volume   = vtk.vtkVolume()

        self._property.ShadeOn()
        self._property.SetInterpolationTypeToLinear()
        self._property.SetAmbient(0.2)
        self._property.SetDiffuse(0.7)
        self._property.SetSpecular(0.3)

        self._volume.SetMapper(self._mapper)
        self._volume.SetProperty(self._property)
        self.vtk_renderer.AddVolume(self._volume)

        self._current_preset = "mri_default"

    # ── Public API ────────────────────────────────────────────────────────────

    def set_volume(
        self,
        data: np.ndarray,
        spacing: tuple[float, float, float] | None = None,
    ) -> None:
        """
        Load a float32 (Z, Y, X) array into the VTK pipeline.

        Data is expected to be normalised to [0, 1] (as returned by loader.py).
        Converts to float32 internally if needed.
        """
        self._data = data.astype(np.float32)
        self._build_image_data(spacing)
        self._apply_preset(self._current_preset)

    def set_preset(self, name: str) -> None:
        """
        Apply a named transfer function preset.

        Args:
            name: One of "mri_default", "bone", "angio", "pet".

        Raises:
            KeyError: If the preset name is not recognised.
        """
        if name not in PRESETS:
            raise KeyError(
                f"Unknown preset '{name}'. "
                f"Available: {list(PRESETS.keys())}"
            )
        self._current_preset = name
        if self._data is not None:
            self._apply_preset(name)

    def preset_names(self) -> list[str]:
        """Return available transfer function preset names."""
        return list(PRESETS.keys())

    def show_standalone(self) -> None:
        """
        Launch a standalone VTK render window (blocking).
        Useful for testing outside of the Qt application.
        """
        if self._data is None:
            raise RuntimeError("No volume data loaded. Call set_volume() first.")

        render_window = vtk.vtkRenderWindow()
        render_window.SetSize(800, 600)
        render_window.SetWindowName("MPRViewer — Volume Rendering")
        render_window.AddRenderer(self.vtk_renderer)

        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(render_window)

        style = vtk.vtkInteractorStyleTrackballCamera()
        interactor.SetInteractorStyle(style)

        render_window.Render()
        interactor.Start()

    def reset_camera(self) -> None:
        """Reset the camera to show the full volume."""
        self.vtk_renderer.ResetCamera()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_image_data(self, spacing: tuple[float, float, float] | None) -> None:
        """Convert numpy array to vtkImageData and connect to mapper."""
        data = self._data
        z, y, x = data.shape

        image_data = vtk.vtkImageData()
        image_data.SetDimensions(x, y, z)
        if spacing is None:
            image_data.SetSpacing(1.0, 1.0, 1.0)
        else:
            sx, sy, sz = spacing
            image_data.SetSpacing(sx, sy, sz)
        image_data.SetOrigin(0.0, 0.0, 0.0)

        vtk_array = numpy_support.numpy_to_vtk(
            data.ravel(order="C"),
            deep=True,
            array_type=vtk.VTK_FLOAT,
        )
        image_data.GetPointData().SetScalars(vtk_array)

        self._image_data = image_data
        self._mapper.SetInputData(image_data)

    def _apply_preset(self, name: str) -> None:
        """Build and apply color and opacity transfer functions from preset."""
        preset = PRESETS[name]

        color_fn = vtk.vtkColorTransferFunction()
        for intensity, r, g, b in preset["color"]:
            color_fn.AddRGBPoint(intensity, r, g, b)

        opacity_fn = vtk.vtkPiecewiseFunction()
        for intensity, opacity in preset["opacity"]:
            opacity_fn.AddPoint(intensity, opacity)

        self._property.SetColor(color_fn)
        self._property.SetScalarOpacity(opacity_fn)