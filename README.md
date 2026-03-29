<div align="center">

# MPRViewer

**Multi-Planar Reconstruction medical image viewer**

[![Docs](https://img.shields.io/badge/docs-github.io-teal)](https://basselshaheen06.github.io/MPR_Viewer)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-teal)](https://www.python.org)

<!-- Replace with actual demo GIF -->
<!-- ![MPRViewer demo](assets/demo/demo.gif) -->

</div>

---

MPRViewer loads NIfTI and DICOM volumes and displays all three orthogonal planes (Axial, Coronal, Sagittal) with synchronized crosshair navigation. A fourth panel embeds VTK GPU ray-cast volume rendering directly in the window.

## Features

| | |
|---|---|
| **MPR planes** | Axial, Coronal, Sagittal — synchronized crosshair |
| **File formats** | NIfTI (`.nii`, `.nii.gz`), DICOM series, single DICOM |
| **Window / Level** | Per-plane W/L controls (radiological standard) |
| **3D rendering** | VTK GPU ray-cast, embedded as 4th viewport |
| **Transfer functions** | MRI default, Bone, Angio, PET presets |
| **Cine mode** | 20 fps animated slice playback |
| **Theme** | Dark (clinical default) + light mode |

## Quick start

```bash
git clone https://github.com/BasselShaheen06/MPR_Viewer.git
cd MPR_Viewer
python -m venv venv
venv\Scripts\activate    # Windows
pip install -r requirements.txt
python main.py
```

→ **[Full documentation](https://basselshaheen06.github.io/MPR_Viewer)**

## Architecture

```
mprviewer/
├── core/
│   ├── loader.py      # NIfTI + DICOM loading — no UI
│   └── renderer.py    # VTK pipeline — no UI
└── ui/
    ├── viewport.py    # SliceViewport widget (reusable, ×3)
    ├── controls.py    # Sidebar panel
    ├── main_window.py # Wiring + crosshair sync
    └── theme.py       # Dark / light palettes
```

`core/` modules are pure functions — no Qt, no matplotlib. They can be used independently in scripts or notebooks.

## License

MIT — Bassel Shaheen, Cairo University SBME