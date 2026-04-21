# core/loader.py

Pure image loading. No UI dependencies.
All public functions return a `VolumeData` object.

---

## `VolumeData`

```python
@dataclass(frozen=True)
class VolumeData:
    data:        np.ndarray                  # float32 (Z, Y, X), values in [0, 1]
    spacing:     tuple[float, float, float]  # physical (sx, sy, sz) in mm
    raw_min:     float                       # original minimum before normalisation
    raw_max:     float                       # original maximum before normalisation
    modality:    str | None                  # e.g. "CT", "MR"
    orientation: str | None                  # e.g. "LPS"
```

---

## `guess_loader`

```python
def guess_loader(path: str | Path) -> VolumeData
```

Auto-detects file type and delegates:

| Input | Loader |
|---|---|
| `.nii`, `.nii.gz` | `load_nifti` |
| `.dcm` | `load_single_dicom` |
| directory | `load_dicom_series` |
| anything else | SimpleITK fallback |

```python
from mlenz.core.loader import guess_loader

vol = guess_loader("brain.nii.gz")
print(vol.data.shape)    # e.g. (182, 218, 182)
print(vol.spacing)       # e.g. (1.0, 1.0, 1.0)
```

---

## `load_nifti`

```python
def load_nifti(path: str | Path) -> VolumeData
```

Loads `.nii` / `.nii.gz`. Applies orientation correction via
`_orient_image()` to ensure consistent LPS+ orientation.

**Raises:** `FileNotFoundError`, `ValueError`

---

## `load_dicom_series`

```python
def load_dicom_series(directory: str | Path) -> VolumeData
```

Loads all DICOM files in a directory, sorted by `ImagePositionPatient`
tag (more reliable than filename sorting).

**Raises:** `FileNotFoundError`, `ValueError`

---

## `load_single_dicom`

```python
def load_single_dicom(path: str | Path) -> VolumeData
```

Loads one `.dcm` file. Returns shape `(1, H, W)` so the rest
of the app treats it uniformly as a 3-D volume.