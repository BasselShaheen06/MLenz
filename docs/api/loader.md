# core/loader.py

Pure image loading. No UI dependencies.
All functions return a `VolumeData` object.

---

## `VolumeData`

```python
@dataclass(frozen=True)
class VolumeData:
    data:        np.ndarray              # float32 (Z, Y, X), values in [0, 1]
    spacing:     tuple[float, float, float]  # (sx, sy, sz) in mm
    raw_min:     float                   # original minimum before normalisation
    raw_max:     float                   # original maximum before normalisation
    modality:    str | None              # DICOM modality tag e.g. "CT", "MR"
    orientation: str | None             # e.g. "LPS"
```

---

## `guess_loader`

```python
def guess_loader(path: str | Path) -> VolumeData
```

Auto-detects file type and calls the appropriate loader.

| Input | Loader called |
|---|---|
| `.nii`, `.nii.gz` | `load_nifti` |
| `.dcm` | `load_single_dicom` |
| directory | `load_dicom_series` |
| other | SimpleITK fallback |

```python
from mprviewer.core.loader import guess_loader

vol = guess_loader("brain.nii.gz")
print(vol.data.shape)    # (182, 218, 182)
print(vol.spacing)       # (1.0, 1.0, 1.0)
print(vol.data.min(), vol.data.max())  # 0.0, 1.0
```

---

## `load_nifti`

```python
def load_nifti(path: str | Path) -> VolumeData
```

Loads `.nii` or `.nii.gz`. Applies orientation correction via
`_orient_image()` to ensure consistent LPS+ orientation.

**Raises:** `FileNotFoundError`, `ValueError`

---

## `load_dicom_series`

```python
def load_dicom_series(directory: str | Path) -> VolumeData
```

Loads all DICOM files in a directory, sorted by `ImagePositionPatient`
tag. More reliable than filename sorting.

**Raises:** `FileNotFoundError`, `ValueError`

---

## `load_single_dicom`

```python
def load_single_dicom(path: str | Path) -> VolumeData
```

Loads one `.dcm` file. Returns shape `(1, H, W)` — a single-slice
volume so the rest of the app can treat it uniformly.