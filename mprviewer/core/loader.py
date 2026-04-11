"""
mprviewer.core.loader
~~~~~~~~~~~~~~~~~~~~~
Medical image loading — NIfTI and DICOM series.

All functions are pure: they take a path, return a normalised float32
numpy array of shape (Z, Y, X). No Qt, no matplotlib, no side effects.

Coordinate convention:
    axis 0 = Z (axial slices, inferior → superior)
    axis 1 = Y (coronal slices, anterior → posterior)
    axis 2 = X (sagittal slices, left → right)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk


@dataclass(frozen=True)
class VolumeData:
    """Normalized volume data with physical spacing metadata."""

    data: np.ndarray
    spacing: tuple[float, float, float]  # (sx, sy, sz)
    raw_min: float
    raw_max: float
    modality: str | None = None
    orientation: str | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_nifti(path: str | Path) -> VolumeData:
    """
    Load a NIfTI file (.nii or .nii.gz).

    Args:
        path: Path to the NIfTI file.

    Returns:
        float32 array of shape (Z, Y, X), values normalised to [0, 1].

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be read as a medical image.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        image = sitk.ReadImage(str(path))
        image, orientation = _orient_image(image)
        array = sitk.GetArrayFromImage(image)      # already (Z, Y, X)
    except Exception as exc:
        raise ValueError(f"Could not read NIfTI file: {path}\n{exc}") from exc

    norm, lo, hi = _normalise(array)
    spacing = _get_spacing(image)
    return VolumeData(
        norm,
        spacing,
        lo,
        hi,
        modality=_get_modality(image),
        orientation=orientation,
    )


def load_dicom_series(directory: str | Path) -> VolumeData:
    """
    Load a DICOM series from a directory.

    SimpleITK automatically sorts slices by position using DICOM metadata,
    which is more reliable than sorting by filename.

    Args:
        directory: Path to the folder containing .dcm files.

    Returns:
        float32 array of shape (Z, Y, X), values normalised to [0, 1].

    Raises:
        FileNotFoundError: If the directory does not exist.
        ValueError: If no DICOM series is found or the series cannot be read.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(directory))
    if not series_ids:
        raise ValueError(f"No DICOM series found in: {directory}")

    # Use the first series found
    file_names = reader.GetGDCMSeriesFileNames(str(directory), series_ids[0])
    reader.SetFileNames(file_names)

    try:
        image = reader.Execute()
        image, orientation = _orient_image(image)
        array = sitk.GetArrayFromImage(image)
    except Exception as exc:
        raise ValueError(
            f"Could not read DICOM series in: {directory}\n{exc}"
        ) from exc

    norm, lo, hi = _normalise(array)
    spacing = _get_spacing(image)
    return VolumeData(
        norm,
        spacing,
        lo,
        hi,
        modality=_get_modality(image),
        orientation=orientation,
    )


def load_single_dicom(path: str | Path) -> VolumeData:
    """
    Load a single DICOM file.

    For single-file DICOM (2D slice), returns a (1, H, W) array so the
    rest of the application can treat it as a 3D volume of depth 1.

    Args:
        path: Path to the .dcm file.

    Returns:
        float32 array of shape (1, H, W) or (Z, Y, X), normalised to [0, 1].
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        image = sitk.ReadImage(str(path))
        image, orientation = _orient_image(image)
        array = sitk.GetArrayFromImage(image)
    except Exception as exc:
        raise ValueError(
            f"Could not read DICOM file: {path}\n{exc}"
        ) from exc

    if array.ndim == 2:
        array = array[np.newaxis, ...]   # (H, W) → (1, H, W)

    norm, lo, hi = _normalise(array)
    spacing = _get_spacing(image)
    return VolumeData(
        norm,
        spacing,
        lo,
        hi,
        modality=_get_modality(image),
        orientation=orientation,
    )


def guess_loader(path: str | Path) -> VolumeData:
    """
    Detect file type and call the appropriate loader.

    Handles:
        .nii, .nii.gz  → load_nifti
        .dcm            → load_single_dicom
        directory       → load_dicom_series

    Args:
        path: Path to file or directory.

    Returns:
        float32 numpy array of shape (Z, Y, X), normalised to [0, 1].
    """
    path = Path(path)
    if path.is_dir():
        return load_dicom_series(path)
    suffix = "".join(path.suffixes).lower()
    if suffix in (".nii", ".nii.gz"):
        return load_nifti(path)
    if suffix == ".dcm":
        return load_single_dicom(path)
    # Fall back to SimpleITK and let it decide
    try:
        image = sitk.ReadImage(str(path))
        image, orientation = _orient_image(image)
        norm, lo, hi = _normalise(sitk.GetArrayFromImage(image))
        spacing = _get_spacing(image)
        return VolumeData(
            norm,
            spacing,
            lo,
            hi,
            modality=_get_modality(image),
            orientation=orientation,
        )
    except Exception as exc:
        raise ValueError(
            f"Unsupported file format or unreadable file: {path}\n{exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise(array: np.ndarray) -> tuple[np.ndarray, float, float]:
    """
    Convert any numeric array to float32 normalised to [0, 1].

    Handles edge case where min == max (uniform volume) by returning zeros.
    """
    array = array.astype(np.float32)
    lo, hi = float(array.min()), float(array.max())
    if hi > lo:
        return (array - lo) / (hi - lo), lo, hi
    return np.zeros_like(array, dtype=np.float32), lo, hi


def _get_spacing(image: sitk.Image) -> tuple[float, float, float]:
    sx, sy, sz = image.GetSpacing()
    return float(sx), float(sy), float(sz)


def _get_modality(image: sitk.Image) -> str | None:
    try:
        if image.HasMetaDataKey("0008|0060"):
            return image.GetMetaData("0008|0060")
    except Exception:
        return None
    return None


def _orient_image(image: sitk.Image, desired: str = "LPS") -> tuple[sitk.Image, str]:
    """Reorient image to a standard coordinate system using SimpleITK."""
    try:
        orienter = sitk.DICOMOrientImageFilter()
        orienter.SetDesiredCoordinateOrientation(desired)
        oriented = orienter.Execute(image)
        return oriented, desired
    except Exception:
        return image, "native"