"""Tests for :mod:`mlenz.core.loader`.

These exercise the public loaders only, using synthetic files written to
``tmp_path`` — no real patient data is required or included.
"""

from __future__ import annotations

import nibabel as nib
import numpy as np
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from mlenz.core.loader import (
    VolumeData,
    guess_loader,
    load_nifti,
    load_single_dicom,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_nifti(
    tmp_path,
    array: np.ndarray,
    spacing: tuple[float, float, float] = (2.0, 3.0, 4.0),
    name: str = "volume.nii.gz",
):
    """Write a NIfTI file with the given voxel array and spacing."""
    affine = np.diag([*spacing, 1.0])
    path = tmp_path / name
    nib.save(nib.Nifti1Image(array.astype(np.int16), affine), str(path))
    return path


def _write_dicom(tmp_path, array: np.ndarray, modality: str = "MR", name="slice.dcm"):
    """Write a minimal single-frame DICOM file readable by SimpleITK."""
    path = tmp_path / name
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.PatientName = "Test^Patient"
    ds.Modality = modality
    ds.Rows, ds.Columns = array.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.ImagePositionPatient = [0, 0, 0]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.PixelSpacing = [0.5, 0.5]
    ds.SliceThickness = 5.0
    ds.PixelData = array.astype(np.uint16).tobytes()
    ds.save_as(str(path))
    return path


# ---------------------------------------------------------------------------
# NIfTI
# ---------------------------------------------------------------------------


def test_load_nifti_returns_volume_data(tmp_path):
    volume = load_nifti(_write_nifti(tmp_path, np.arange(4 * 5 * 6).reshape(4, 5, 6)))

    assert isinstance(volume, VolumeData)
    assert volume.data.dtype == np.float32
    assert volume.orientation == "LPS"


def test_load_nifti_normalises_to_unit_range(tmp_path):
    volume = load_nifti(_write_nifti(tmp_path, np.arange(4 * 5 * 6).reshape(4, 5, 6)))

    assert volume.data.min() == pytest.approx(0.0)
    assert volume.data.max() == pytest.approx(1.0)
    assert volume.raw_min == pytest.approx(0.0)
    assert volume.raw_max == pytest.approx(119.0)


def test_load_nifti_reorders_voxel_axes_to_zyx(tmp_path):
    """NIfTI is (X, Y, Z); MLenz stores (Z, Y, X)."""
    volume = load_nifti(_write_nifti(tmp_path, np.arange(4 * 5 * 6).reshape(4, 5, 6)))

    assert volume.data.shape == (6, 5, 4)


def test_load_nifti_preserves_spacing(tmp_path):
    volume = load_nifti(
        _write_nifti(tmp_path, np.zeros((3, 3, 3)), spacing=(2.0, 3.0, 4.0))
    )

    assert volume.spacing == pytest.approx((2.0, 3.0, 4.0))


def test_load_nifti_uniform_volume_returns_zeros(tmp_path):
    volume = load_nifti(_write_nifti(tmp_path, np.full((3, 3, 3), 7)))

    assert volume.data.min() == 0.0
    assert volume.data.max() == 0.0
    assert volume.raw_min == pytest.approx(7.0)
    assert volume.raw_max == pytest.approx(7.0)


def test_load_nifti_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_nifti(tmp_path / "does-not-exist.nii.gz")


def test_load_nifti_corrupt_file_raises_value_error(tmp_path):
    bad = tmp_path / "broken.nii.gz"
    bad.write_bytes(b"not a nifti file")

    with pytest.raises(ValueError):
        load_nifti(bad)


# ---------------------------------------------------------------------------
# DICOM
# ---------------------------------------------------------------------------


def test_load_single_dicom_returns_depth_one_volume(tmp_path):
    data = np.arange(8 * 10).reshape(8, 10)
    volume = load_single_dicom(_write_dicom(tmp_path, data))

    assert volume.data.shape == (1, 8, 10)
    assert volume.raw_min == pytest.approx(0.0)
    assert volume.raw_max == pytest.approx(79.0)
    assert volume.data.max() == pytest.approx(1.0)


def test_load_single_dicom_preserves_modality(tmp_path):
    """The orientation filter drops metadata, so it must be read beforehand."""
    volume = load_single_dicom(_write_dicom(tmp_path, np.zeros((8, 10)), modality="CT"))

    assert volume.modality == "CT"


def test_load_single_dicom_preserves_in_plane_spacing(tmp_path):
    volume = load_single_dicom(_write_dicom(tmp_path, np.zeros((8, 10))))

    assert volume.spacing[0] == pytest.approx(0.5)
    assert volume.spacing[1] == pytest.approx(0.5)


def test_load_single_dicom_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_single_dicom(tmp_path / "missing.dcm")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_guess_loader_dispatches_nifti(tmp_path):
    path = _write_nifti(tmp_path, np.arange(27).reshape(3, 3, 3))

    assert guess_loader(path).data.shape == (3, 3, 3)


def test_guess_loader_dispatches_dicom(tmp_path):
    path = _write_dicom(tmp_path, np.zeros((8, 10)))

    assert guess_loader(path).data.shape == (1, 8, 10)


def test_guess_loader_rejects_unsupported_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello")

    with pytest.raises(ValueError):
        guess_loader(path)


def test_volume_data_is_immutable(tmp_path):
    volume = load_nifti(_write_nifti(tmp_path, np.zeros((3, 3, 3))))

    with pytest.raises(Exception):
        volume.spacing = (9.0, 9.0, 9.0)
