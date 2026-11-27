"""Tests for the synthetic CT phantom and the sample-DICOM generator.

The phantom exists so the CT path can be demonstrated without patient data;
these tests keep it anatomically and numerically honest.
"""

from __future__ import annotations

import numpy as np
import pytest

from mlenz.core.loader import load_single_dicom
from mlenz.core.phantom import AIR, BRAIN, head_ct
from mlenz.core.windowing import get_preset, is_ct, to_hounsfield, window
from tools.make_sample_ct import write_sample_ct

# ---------------------------------------------------------------------------
# The phantom itself
# ---------------------------------------------------------------------------


def test_head_ct_has_the_requested_shape_and_dtype():
    hu = head_ct(size=64, slices=16)

    assert hu.shape == (16, 64, 64)
    assert hu.dtype == np.float32


def test_head_ct_stays_inside_physical_hounsfield_limits():
    hu = head_ct(size=64, slices=16)

    assert float(hu.min()) >= -1024.0
    assert float(hu.max()) <= 3071.0


def test_head_ct_contains_air_brain_and_bone():
    hu = head_ct(size=96, slices=24)
    middle = hu[12]

    assert float(middle[0, 0]) == pytest.approx(AIR)          # outside the head
    assert abs(float(middle[48, 48]) - BRAIN) < 25.0          # brain parenchyma
    assert float(middle.max()) > 800.0                        # skull


def test_head_ct_is_reproducible_and_seed_dependent():
    a = head_ct(size=48, slices=8, seed=1)
    b = head_ct(size=48, slices=8, seed=1)
    c = head_ct(size=48, slices=8, seed=2)

    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_head_ct_rejects_degenerate_sizes():
    with pytest.raises(ValueError):
        head_ct(size=16)
    with pytest.raises(ValueError):
        head_ct(slices=2)


# ---------------------------------------------------------------------------
# The written sample
# ---------------------------------------------------------------------------


def test_sample_ct_loads_as_a_ct_volume(tmp_path):
    path = write_sample_ct(tmp_path / "ct.dcm", size=64, slices=12)

    volume = load_single_dicom(path)

    assert is_ct(volume)
    assert volume.rescale_applied is True
    assert volume.data.shape == (12, 64, 64)


def test_sample_ct_round_trips_hounsfield_units(tmp_path):
    path = write_sample_ct(tmp_path / "ct.dcm", size=64, slices=12)

    hu = to_hounsfield(load_single_dicom(path))

    assert float(hu.min()) == pytest.approx(AIR, abs=1.0)
    assert float(hu.max()) > 900.0


def test_brain_preset_separates_the_lesion_from_parenchyma(tmp_path):
    """The point of the phantom: a window that shows the lesion."""
    path = write_sample_ct(tmp_path / "ct.dcm", size=96, slices=24)
    hu = to_hounsfield(load_single_dicom(path))
    middle = hu[12]

    display = window(middle, get_preset("Brain").level, get_preset("Brain").width)

    # Brain sits in the mid-grey range, the lesion near white, air at black.
    assert 0.2 < float(display[48, 48]) < 0.8
    assert float(display[0, 0]) == pytest.approx(0.0)
    assert float(display.max()) == pytest.approx(1.0)
