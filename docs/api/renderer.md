# core/renderer.py

VTK GPU volume rendering pipeline. No UI or Qt dependencies.

---

## `VolumeRenderer`

```python
from mprviewer.core.renderer import VolumeRenderer

renderer = VolumeRenderer()
renderer.set_volume(vol.data, spacing=vol.spacing)
renderer.set_preset("mri_default")
```

### Methods

| Method | Description |
|---|---|
| `set_volume(data, spacing)` | Load float32 (Z,Y,X) array into VTK pipeline |
| `set_preset(name)` | Apply named transfer function preset |
| `preset_names()` | Returns `["mri_default", "bone", "angio", "pet"]` |
| `reset_camera()` | Fit camera to show the full volume |
| `show_standalone()` | Launch blocking standalone VTK window (for testing) |

### Transfer function presets

| Name | Colour strategy | Opacity strategy |
|---|---|---|
| `mri_default` | Black → grey → white | Transparent below 0.1, opaque above 0.7 |
| `bone` | Black → tan → white | Only high intensities (> 0.6) opaque |
| `angio` | Black → red → orange → white | Mid-to-high intensities visible |
| `pet` | Black → blue → cyan → yellow → white | Low counts transparent |

### Embedding in Qt

```python
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

vtk_widget = QVTKRenderWindowInteractor(parent_widget)
vtk_widget.GetRenderWindow().AddRenderer(renderer.vtk_renderer)

import vtk
style = vtk.vtkInteractorStyleTrackballCamera()
vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(style)
```

### Custom transfer function

```python
import vtk

color_fn = vtk.vtkColorTransferFunction()
color_fn.AddRGBPoint(0.0, 0.0, 0.0, 0.0)   # intensity 0 → black
color_fn.AddRGBPoint(0.5, 0.8, 0.2, 0.0)   # intensity 0.5 → orange
color_fn.AddRGBPoint(1.0, 1.0, 1.0, 0.9)   # intensity 1 → near-white

opacity_fn = vtk.vtkPiecewiseFunction()
opacity_fn.AddPoint(0.0, 0.0)
opacity_fn.AddPoint(0.3, 0.1)
opacity_fn.AddPoint(1.0, 0.9)

renderer._property.SetColor(color_fn)
renderer._property.SetScalarOpacity(opacity_fn)
```