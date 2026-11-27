"""Tests for :mod:`mlenz.core.windowing`.

The end-to-end case matters most: it is the only test that proves the whole
chain — DICOM header -> preserved metadata -> normalised array -> Hounsfield
units — because each link was broken at some point.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from mlenz.core.loader import VolumeData, load_single_dicom
from mlenz.core.windowing import (
    PRESETS,
    NotCTError,
    get_preset,
    has_rescale,
    is_ct,
    rescale,
    to_hounsfield,
    to_normalised_window,
    to_raw,
    window,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _volume(
    values, raw_min, raw_max, modality="CT", meta=None, rescale_applied=False
) -> VolumeData:
    """Build a VolumeData whose normalised data reconstructs to ``values``."""
    return VolumeData(
        data=np.asarray(values, dtype=np.float32),
        spacing=(1.0, 1.0, 1.0),
        raw_min=raw_min,
        raw_max=raw_max,
        modality=modality,
        meta=meta or {},
        rescale_applied=rescale_applied,
    )


def _ct_volume(hounsfield, slope=1.0, intercept=-1024.0, modality="CT") -> VolumeData:
    """Build a CT volume that would produce ``hounsfield`` after rescaling."""
    hu = np.asarray(hounsfield, dtype=np.float32)
    stored = (hu - intercept) / slope
    lo, hi = float(stored.min()), float(stored.max())
    norm = (stored - lo) / (hi - lo) if hi > lo else np.zeros_like(stored)
    return _volume(
        norm,
        lo,
        hi,
        modality=modality,
        meta={"0028|1053": str(slope), "0028|1052": str(intercept)},
    )


def _write_ct_dicom(tmp_path, stored_values, slope=1.0, intercept=-1024.0):
    """Write a single-frame CT DICOM carrying rescale tags."""
    path = tmp_path / "ct.dcm"
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.PatientName = "Test^Patient"
    ds.Modality = "CT"
    ds.Rows, ds.Columns = stored_values.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.RescaleSlope = slope
    ds.RescaleIntercept = intercept
    ds.ImagePositionPatient = [0, 0, 0]
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.PixelSpacing = [0.5, 0.5]
    ds.SliceThickness = 1.0
    ds.PixelData = stored_values.astype(np.uint16).tobytes()
    ds.save_as(str(path))
    return path


# ---------------------------------------------------------------------------
# to_raw
# ---------------------------------------------------------------------------


def test_to_raw_undoes_normalisation():
    volume = _volume([0.0, 0.5, 1.0], raw_min=-100.0, raw_max=100.0, modality="MR")

    assert to_raw(volume) == pytest.approx([-100.0, 0.0, 100.0])


def test_to_raw_handles_a_uniform_volume():
    volume = _volume([0.0, 0.0], raw_min=7.0, raw_max=7.0, modality="MR")

    assert to_raw(volume) == pytest.approx([7.0, 7.0])


# ---------------------------------------------------------------------------
# Hounsfield conversion
# ---------------------------------------------------------------------------


def test_to_hounsfield_recovers_known_values():
    volume = _ct_volume([-1000.0, 0.0, 40.0, 80.0, 1000.0])

    assert to_hounsfield(volume) == pytest.approx(
        [-1000.0, 0.0, 40.0, 80.0, 1000.0], abs=1e-3
    )


def test_to_hounsfield_applies_slope_and_intercept():
    volume = _ct_volume([0.0, 100.0], slope=2.0, intercept=-1000.0)

    assert rescale(volume) == (2.0, -1000.0)
    assert to_hounsfield(volume) == pytest.approx([0.0, 100.0], abs=1e-3)


def test_to_hounsfield_rejects_mri_without_rescale_tags():
    volume = _volume([0.0, 1.0], raw_min=0.0, raw_max=1000.0, modality="MR")

    with pytest.raises(NotCTError):
        to_hounsfield(volume)


def test_to_hounsfield_accepts_rescale_tags_without_a_ct_modality():
    volume = _ct_volume([40.0], modality=None)

    assert to_hounsfield(volume) == pytest.approx([40.0], abs=1e-3)


def test_to_hounsfield_does_not_apply_the_rescale_twice():
    """A loader-built CT already holds HU; the tags must not shift it again."""
    volume = _volume(
        [0.0, 0.5, 1.0],
        raw_min=-1000.0,
        raw_max=1000.0,
        meta={"0028|1053": "1.0", "0028|1052": "-1024.0"},
        rescale_applied=True,
    )

    assert to_hounsfield(volume) == pytest.approx([-1000.0, 0.0, 1000.0])


def test_rescale_defaults_to_identity_when_tags_are_missing():
    assert rescale(_volume([0.0], 0.0, 1.0, modality="CT")) == (1.0, 0.0)


def test_rescale_ignores_a_zero_slope():
    volume = _volume([0.0], 0.0, 1.0, meta={"0028|1053": "0", "0028|1052": "-1024"})

    assert rescale(volume) == (1.0, -1024.0)


def test_rescale_ignores_unparseable_tags():
    volume = _volume([0.0], 0.0, 1.0, meta={"0028|1053": "abc", "0028|1052": ""})

    assert rescale(volume) == (1.0, 0.0)


def test_is_ct_and_has_rescale_describe_the_headers():
    ct = _ct_volume([0.0])
    mr = _volume([0.0], 0.0, 1.0, modality="mr")

    assert is_ct(ct) and has_rescale(ct)
    assert not is_ct(mr) and not has_rescale(mr)


def test_hounsfield_survives_a_real_dicom_round_trip(tmp_path):
    """DICOM -> loader -> normalised -> HU must return the scanner's values."""
    stored = np.arange(64, dtype=np.uint16).reshape(8, 8)

    volume = load_single_dicom(_write_ct_dicom(tmp_path, stored))

    # SimpleITK already applied the rescale while reading, so the loader must
    # say so and to_hounsfield must not shift the values a second time.
    assert volume.rescale_applied is True
    expected = np.sort((stored.astype(np.float32) - 1024.0).ravel())
    assert np.sort(to_hounsfield(volume).ravel()) == pytest.approx(expected, abs=1e-3)


# ---------------------------------------------------------------------------
# Windowing
# ---------------------------------------------------------------------------


def test_window_maps_the_level_to_the_midpoint():
    assert window(np.array([40.0]), level=40.0, width=80.0) == pytest.approx([0.5])


def test_window_clips_outside_the_range():
    result = window(np.array([-1000.0, 1000.0]), level=40.0, width=80.0)

    assert result == pytest.approx([0.0, 1.0])


def test_window_edges_map_to_zero_and_one():
    result = window(np.array([0.0, 80.0]), level=40.0, width=80.0)

    assert result == pytest.approx([0.0, 1.0])


@pytest.mark.parametrize("width", [0.0, -10.0])
def test_window_rejects_non_positive_width(width):
    with pytest.raises(ValueError):
        window(np.array([0.0]), level=0.0, width=width)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


def test_presets_carry_the_standard_clinical_values():
    expected = {
        "Brain": (40, 80),
        "Bone": (400, 1800),
        "Lung": (-600, 1500),
        "Soft tissue": (40, 400),
    }

    for name, (level, width) in expected.items():
        preset = get_preset(name)
        assert (preset.level, preset.width) == (level, width)


def test_preset_names_are_unique():
    names = [p.name.casefold() for p in PRESETS]

    assert len(names) == len(set(names))


def test_get_preset_is_case_insensitive():
    assert get_preset("  bRaIn ").name == "Brain"


def test_get_preset_reports_what_is_available():
    with pytest.raises(KeyError, match="Brain"):
        get_preset("nope")


def test_preset_apply_uses_its_own_window():
    brain = get_preset("Brain")

    assert brain.apply(np.array([40.0])) == pytest.approx([0.5])


# ---------------------------------------------------------------------------
# Translating a window onto the normalised slider scale
# ---------------------------------------------------------------------------


def test_normalised_window_maps_hu_onto_the_unit_range():
    volume = _volume(
        [0.0, 1.0], raw_min=-1024.0, raw_max=3071.0, rescale_applied=True
    )

    level, width = to_normalised_window(volume, 40.0, 80.0)

    assert level == pytest.approx((40.0 + 1024.0) / 4095.0)
    assert width == pytest.approx(80.0 / 4095.0)


def test_normalised_window_agrees_with_windowing_the_hu_directly():
    """The slider path and the HU path must produce the same picture."""
    volume = _volume(
        np.linspace(0.0, 1.0, 11),
        raw_min=-1024.0,
        raw_max=3071.0,
        rescale_applied=True,
    )

    level, width = to_normalised_window(volume, 40.0, 400.0)

    assert window(volume.data, level, width) == pytest.approx(
        window(to_hounsfield(volume), 40.0, 400.0), abs=1e-6
    )


def test_normalised_window_undoes_a_rescale_the_loader_did_not_apply():
    # Stored values are 1024..1124, i.e. HU 0..100 once rescaled.
    volume = _ct_volume([0.0, 100.0])

    level, width = to_normalised_window(volume, 40.0, 80.0)

    assert level == pytest.approx(0.4)
    assert width == pytest.approx(0.8)


def test_normalised_window_rejects_a_flat_volume():
    volume = _volume([0.0], raw_min=5.0, raw_max=5.0, modality="CT")

    with pytest.raises(ValueError):
        to_normalised_window(volume, 40.0, 80.0)
