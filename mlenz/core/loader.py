"""
mlenz.core.loader
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

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import SimpleITK as sitk


@dataclass(frozen=True)
class VolumeData:
    """A loaded volume plus the physical facts needed to interpret it.

    Two axis orders meet in this object, so both are stated explicitly:

    * ``data`` follows numpy convention and is ``(Z, Y, X)``.
    * ``spacing`` follows the image header and is ``(sx, sy, sz)`` — the
      physical size in millimetres of one voxel along X, Y and Z.

    Use :attr:`spacing_zyx` whenever multiplying against ``data.shape``;
    doing it by hand is how organ volumes end up silently wrong.
    """

    data: np.ndarray
    spacing: tuple[float, float, float]  # (sx, sy, sz)
    raw_min: float
    raw_max: float
    modality: str | None = None
    orientation: str | None = None
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def spacing_zyx(self) -> tuple[float, float, float]:
        """Voxel spacing in the same axis order as ``data``: ``(sz, sy, sx)``."""
        sx, sy, sz = self.spacing
        return sz, sy, sx

    @property
    def physical_extent(self) -> tuple[float, float, float]:
        """Volume size in millimetres as ``(extent_z, extent_y, extent_x)``."""
        return tuple(dim * step for dim, step in zip(self.data.shape, self.spacing_zyx))


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
        # Capture DICOM metadata first: DICOMOrientImageFilter drops every
        # metadata key, so reading tags after reorientation returns nothing.
        meta = _get_meta(image)
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
        modality=meta.get("0008|0060"),
        meta=meta,
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
        meta = _get_meta(image)
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
        modality=meta.get("0008|0060"),
        meta=meta,
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
        meta = _get_meta(image)
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
        modality=meta.get("0008|0060"),
        meta=meta,
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
        meta = _get_meta(image)
        image, orientation = _orient_image(image)
        norm, lo, hi = _normalise(sitk.GetArrayFromImage(image))
        spacing = _get_spacing(image)
        return VolumeData(
            norm,
            spacing,
            lo,
            hi,
            modality=meta.get("0008|0060"),
        meta=meta,
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


def _get_meta(image: sitk.Image) -> dict[str, str]:
    """Return every metadata key on the image, as a plain dict.

    Must be called *before* reorientation: ``DICOMOrientImageFilter`` drops
    all metadata, so tags read afterwards come back empty.
    """
    try:
        return {key: image.GetMetaData(key) for key in image.GetMetaDataKeys()}
    except Exception:
        return {}


def _orient_image(image: sitk.Image, desired: str = "LPS") -> tuple[sitk.Image, str]:
    """Reorient image to a standard coordinate system using SimpleITK."""
    try:
        orienter = sitk.DICOMOrientImageFilter()
        orienter.SetDesiredCoordinateOrientation(desired)
        oriented = orienter.Execute(image)
        return oriented, desired
    except Exception:
        return image, "native"