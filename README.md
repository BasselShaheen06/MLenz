<div align="center">

# MPRViewer

**Multi-Planar Reconstruction medical image viewer**

[![Docs](https://img.shields.io/badge/docs-github.io-teal)](https://basselshaheen06.github.io/MPR_Viewer)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-teal)](https://www.python.org)

<!-- DEMO GIF — record with ScreenToGif: load volume → drag crosshair → 3D panel → annotate → save -->
<!-- ![MPRViewer demo](assets/demo/demo.gif) -->

</div>

---

MPRViewer loads NIfTI and DICOM volumes and displays all three orthogonal
planes with synchronized, draggable crosshair navigation. A fourth panel
embeds VTK GPU ray-cast volume rendering.

## Screenshots

<!-- Replace with actual screenshots after first run -->
<!-- ![Main view — three MPR planes](assets/demo/screenshot_main.png) -->
<!-- ![Annotation mode](assets/demo/screenshot_annotate.png) -->
<!-- ![3D volume rendering panel](assets/demo/screenshot_3d.png) -->
<!-- ![Light mode](assets/demo/screenshot_light.png) -->

## Features

| | |
|---|---|
| **MPR planes** | Axial, Coronal, Sagittal — synchronized |
| **Crosshairs** | Draggable — drag any line, all planes update in real time |
| **Formats** | NIfTI `.nii`/`.nii.gz`, DICOM series, single DICOM |
| **Per-viewport controls** | Play/Pause, W/L sliders, colormap — embedded per plane |
| **Annotation mode** | Freehand drawing on any plane, export as PNG |
| **3D rendering** | VTK GPU ray-cast, embedded as 4th viewport |
| **Transfer functions** | MRI default, Bone, Angio, PET presets |
| **Theme** | Dark (clinical default) + light mode toggle |
| **Background loading** | QThread — UI stays responsive on large volumes |

## Quick start

```bash
git clone https://github.com/BasselShaheen06/MPR_Viewer.git
cd MPR_Viewer
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # macOS / Linux
pip install -r requirements.txt
python main.py
```

→ **[Full documentation](https://basselshaheen06.github.io/MPR_Viewer)**

## Architecture

```
mprviewer/
├── core/
│   ├── loader.py     # NIfTI + DICOM loading, VolumeData dataclass — no UI
│   └── renderer.py   # VTK pipeline, transfer function presets — no UI
└── ui/
    ├── viewport.py   # SliceViewport — pyqtgraph canvas, crosshairs, annotation
    ├── controls.py   # TopBar
    ├── main_window.py# Wiring, crosshair sync, cine, background load
    └── theme.py      # Dark / light palettes
```

## Development

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
ruff check .
pytest
```

## License

MIT — Bassel Shaheen, Cairo University SBME