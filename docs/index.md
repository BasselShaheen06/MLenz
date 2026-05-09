# MLenz

**Multi-Planar Reconstruction MRI viewer — NIfTI, DICOM, embedded 3D volume rendering.**

---

## Demo

### MLenz demo 2.0

<video controls width="100%">
    <source src="assets/demo/MLenzDemo%202.0.mp4" type="video/mp4">
    Your browser does not support the video tag.
</video>

### MLenz demo 1.0

<video controls width="100%">
    <source src="assets/demo/demo%201.0.mp4" type="video/mp4">
    Your browser does not support the video tag.
</video>

---

## Screenshots

### Entry window
![Entry window](assets/screenshots/Entry%20Window.png)

### Main view
![Main view](assets/screenshots/Screenshot%202026-04-20%20222749.png)

### 2x2 grid with 3D panel
![2x2 grid with 3D panel](assets/screenshots/Screenshot%202026-04-21%20052912.png)

### Different color mapping
![Different color mapping](assets/screenshots/Different%20Color%20Mapping.png)

### Window/Level controls
![Window/Level](assets/screenshots/Window-Level.png)

### Draw annotations
![Draw annotations](assets/screenshots/Draw%20Annotations.png)

### Annotations fade with slices
![Annotations fade with slices](assets/screenshots/Annotations%20fade%20with%20slices.png)

### 3D construction using VTK
![3D construction using VTK](assets/screenshots/3D%20Construction%20using%20VTK.png)

### Light mode
![Light mode](assets/screenshots/LightMode.png)

---

## At a glance

| Feature | Details |
|---|---|
| **File formats** | NIfTI `.nii`/`.nii.gz` · single DICOM `.dcm` |
| **MPR planes** | Axial · Coronal · Sagittal — synchronized |
| **Crosshairs** | Draggable — move any line, all three planes update in real time |
| **Crosshair circle** | Hollow red dot marks the intersection point |
| **Per-viewport controls** | Play/Pause · colormap · W/L sliders — embedded in each viewport |
| **Global cine** | ▶ All / ⏸ All — play every plane together |
| **Annotation** | Freehand drawing, clear, export viewport as PNG |
| **3D rendering** | VTK GPU ray-cast embedded as 4th panel |
| **Transfer functions** | MRI default · Bone · Angio · PET presets |
| **Theme** | Dark (clinical default) + light mode toggle |
| **Background loading** | QThread — UI stays responsive |
| **Slice cache** | LRU + prefetch for fast navigation |
| **Start screen** | fMRI-style gradient splash with dark overlay |
| **Guided tour** | Step-by-step overlay with spotlight prompts |

---

## Architecture

```mermaid
graph TD
    A["main.py"] --> B["ui/main_window.py\nMainWindow"]
    B --> C["ui/controls.py\nTopBar"]
    B --> D["ui/viewport.py\nSliceViewport ×3\nInfiniteLine crosshairs\nAnnotation layer"]
    B --> E["ui/theme.py\nThemeManager"]
    B --> F["core/loader.py\nVolumeData · guess_loader"]
    B --> G["core/renderer.py\nVolumeRenderer · VTK pipeline"]
```

**Hard boundary:** `core/` never imports PyQt5, pyqtgraph, or matplotlib.

---

## Quick start

```bash
git clone https://github.com/BasselShaheen06/MLenz.git
cd MLenz
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
python main.py
```