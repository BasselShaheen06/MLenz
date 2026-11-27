"""Tests for :mod:`mlenz.core.geometry`."""

from __future__ import annotations

import pytest

from mlenz.core.geometry import aspect_scale


def test_square_pixels_need_no_scaling():
    assert aspect_scale(1.0, 1.0) == pytest.approx(1.0)


def test_tall_pixels_are_compressed_horizontally():
    # 1 mm across, 2 mm down: a column is half as wide as a row is tall.
    assert aspect_scale(1.0, 2.0) == pytest.approx(0.5)


def test_wide_pixels_are_stretched_horizontally():
    assert aspect_scale(2.0, 1.0) == pytest.approx(2.0)


def test_anisotropic_slice_thickness_matches_physical_width():
    # 0.5 x 0.5 mm in-plane, 5 mm slice thickness -> coronal/sagittal views.
    assert aspect_scale(0.5, 5.0) == pytest.approx(0.1)


@pytest.mark.parametrize("col,row", [(0.0, 1.0), (1.0, 0.0), (-1.0, 1.0), (1.0, -1.0)])
def test_invalid_spacing_falls_back_to_one(col, row):
    assert aspect_scale(col, row) == pytest.approx(1.0)
