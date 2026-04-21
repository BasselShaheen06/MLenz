# Installation

## Requirements

- Python 3.10 or later
- A GPU with OpenGL support (for VTK volume rendering)
- Windows, macOS, or Linux

## Step 1 — Clone

```bash
git clone https://github.com/BasselShaheen06/MLenz.git
cd MLenz
```

## Step 2 — Virtual environment

=== "Windows"
    ```powershell
    python -m venv venv
    venv\Scripts\activate
    ```
=== "macOS / Linux"
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

## Step 3 — Install

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `PyQt5` | GUI framework |
| `pyqtgraph` | Main canvas — zoom, pan, draggable crosshairs |
| `SimpleITK` | NIfTI and DICOM reading |
| `vtk` | GPU volume rendering |
| `matplotlib` | Colormaps (via pyqtgraph) |
| `numpy` | Array operations |
| `pydicom` | Single-file DICOM support |
| `nibabel` | NIfTI metadata |

## Step 4 — Run

```bash
python main.py
```

---

## Test data

The `Dataset/` folder contains a sample brain NIfTI file. Load it with
**Load NIfTI** to verify the installation.

**Other free datasets:**

| Source | URL | Format |
|---|---|---|
| OpenNeuro | openneuro.org | NIfTI |
| IXI Dataset | brain-development.org/ixi-dataset | NIfTI |
| TCIA | cancerimagingarchive.net | DICOM |
| OsiriX sample data | osirix-viewer.com/resources/dicom-image-library | DICOM |

---

## VTK GPU note

If you see a warning about `QVTKRenderWindowInteractor`, upgrade VTK:

```bash
pip install --upgrade vtk
```

Without a discrete GPU, VTK falls back to software rendering — slower
but functional.

---

## Building the docs locally

```bash
pip install mkdocs-material
mkdocs serve
# open http://127.0.0.1:8000
```