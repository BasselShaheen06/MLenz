# core/renderer.py

VTK GPU volume rendering pipeline. No UI or Qt dependencies.

---

## `VolumeRenderer`

```python
from mlenz.core.renderer import VolumeRenderer

renderer = VolumeRenderer()
renderer.set_volume(vol.data, spacing=vol.spacing)
renderer.set_preset("mri_default")
```

### Methods

| Method | Description |
|---|---|
| `set_volume(data, spacing)` | Load float32 (Z,Y,X) array into VTK pipeline |
| `set_preset(name)` | Apply named transfer function preset |
| `preset_names()` | `["mri_default", "bone", "angio", "pet"]` |
| `reset_camera()` | Fit camera to full volume |
| `show_standalone()` | Launch blocking VTK window (for testing) |

### Transfer function presets

| Name | Best for |
|---|---|
| `mri_default` | General MRI, soft tissue |
| `bone` | CT, bony structures |
| `angio` | MRA/CTA, vessels |
| `pet` | PET, hot-metal colormap |

### Embedding in Qt

```python
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

vtk_widget = QVTKRenderWindowInteractor(parent_widget)
vtk_widget.GetRenderWindow().AddRenderer(renderer.vtk_renderer)

style = vtk.vtkInteractorStyleTrackballCamera()
vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(style)
```