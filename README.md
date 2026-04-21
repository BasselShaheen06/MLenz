<div align="center">

# MLenz

**Multi-Planar Reconstruction MRI viewer**

[![Docs](https://img.shields.io/badge/docs-github.io-teal)](https://basselshaheen06.github.io/MLenz)
[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-teal)](https://www.python.org)

</div>

---

MLenz loads NIfTI and single-file DICOM scans and displays all three orthogonal
planes — Axial, Coronal, Sagittal — with synchronized draggable crosshairs.
A fourth panel embeds VTK GPU ray-cast volume rendering. Each viewport has
its own embedded controls: play/pause cine, colormap, Window/Level sliders,
freehand annotation, and PNG export.

---

## Demo

> 📹 **Demo coming soon** — record with ScreenToGif:
> load volume → drag crosshair across all planes → switch colormap →
> enable 3D panel → annotate a slice → save annotated PNG

<!-- Once recorded, replace the line below: -->
<!-- ![MLenz demo](assets/demo/demo.gif) -->

---

## Screenshots

> 📸 **Screenshots coming soon** — capture after first successful run

<!-- Uncomment once screenshots are taken:

### Three synchronized MPR planes
![Three MPR planes with draggable crosshairs](assets/demo/screenshot_main.png)

### Per-viewport controls
![Per-viewport play, colormap, W/L, annotation](assets/demo/screenshot_controls.png)

### Annotation mode
![Freehand annotation on a brain MRI slice](assets/demo/screenshot_annotate.png)

### 3D volume rendering
![Embedded VTK volume rendering panel](assets/demo/screenshot_3d.png)

### Light mode
![Light mode with teal accent](assets/demo/screenshot_light.png)

-->

---

## Features

| Feature | Details |
|---|---|
| **MPR planes** | Axial · Coronal · Sagittal — synchronized |
| **Crosshairs** | Draggable `InfiniteLine` — drag any line to update all planes |
| **Crosshair circle** | Hollow red circle marks the intersection point |
| **File formats** | NIfTI `.nii`/`.nii.gz` · single DICOM `.dcm` |
| **Per-viewport controls** | ▶ Play/Pause · colormap · W slider · L slider — embedded in each plane |
| **Global cine** | ▶ All / ⏸ All — play every plane together |
| **Annotation mode** | Freehand drawing, clear, export as PNG |
| **3D rendering** | VTK GPU ray-cast embedded as 4th viewport |
| **Transfer functions** | MRI default · Bone · Angio · PET |
| **Theme** | Dark (clinical default, follows system) + light mode toggle |
| **Background loading** | `QThread` — UI stays responsive on large volumes |
| **Slice cache** | LRU cache + neighbor prefetch for fast navigation |
| **Start screen** | fMRI-style gradient splash with dark overlay |
| **Guided tour** | Step-by-step overlay with spotlight prompts |

---

## Quick start

```bash
git clone https://github.com/BasselShaheen06/MLenz.git
cd MLenz
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # macOS / Linux
pip install -r requirements.txt
python main.py
```

→ **[Full documentation](https://basselshaheen06.github.io/MLenz)**

---

## Architecture

```
mlenz/
├── core/
│   ├── loader.py      # NIfTI + DICOM loading, VolumeData dataclass — no UI
│   └── renderer.py    # VTK pipeline, transfer function presets — no UI
└── ui/
    ├── viewport.py    # SliceViewport — pyqtgraph canvas, crosshairs, annotation
    ├── controls.py    # TopBar (global actions)
    ├── main_window.py # Wiring, crosshair sync, cine timers, background load
    └── theme.py       # Dark / light palettes, ThemeManager
```

`core/` modules have no UI dependencies — they work in scripts and notebooks.

---

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

---

## License

MIT — Bassel Shaheen, Cairo University SBME