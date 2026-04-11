import numpy as np
import pytest

from mprviewer.core import loader


def test_normalise_uniform_volume_returns_zeros():
    data = np.full((2, 3, 4), 5.0, dtype=np.float32)
    out, lo, hi = loader._normalise(data)
    assert out.shape == data.shape
    assert np.allclose(out, 0.0)
    assert lo == 5.0
    assert hi == 5.0


def test_normalise_scales_range_to_unit():
    data = np.array([0.0, 5.0, 10.0], dtype=np.float32)
    out, lo, hi = loader._normalise(data)
    assert np.isclose(out.min(), 0.0)
    assert np.isclose(out.max(), 1.0)
    assert lo == 0.0
    assert hi == 10.0


def test_guess_loader_unknown_file_raises(tmp_path):
    path = tmp_path / "unknown.xyz"
    path.write_text("not a medical image")
    with pytest.raises(ValueError):
        loader.guess_loader(path)
