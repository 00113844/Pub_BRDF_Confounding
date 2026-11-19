"""Checks on the geometry look-up table."""

import numpy as np
import pytest

from publication_spectral_data.indices import INDEX_BANDS, compute_index
from publication_spectral_data.lut import GeometryLUT, build_lut, cached_lut
from publication_spectral_data.prosail_engine import CanopyParams, simulate

PARAMS = CanopyParams(lai=3.0)
SZA = np.arange(20.0, 51.0, 2.0)
VZA = np.arange(0.0, 13.0, 2.0)
RAA = np.array([0, 5, 10, 20, 40, 60, 90, 120, 150, 180], dtype=float)


@pytest.fixture(scope="module")
def lut():
    return build_lut(PARAMS, SZA, VZA, RAA)


def test_nodes_equal_direct_simulation(lut):
    spec = simulate(PARAMS, 30.0, 6.0, 120.0)["rsot"]
    bands = lut.bands_at(30.0, 6.0, 120.0)
    for wl in INDEX_BANDS:
        assert bands[wl] == pytest.approx(spec[wl - 400], abs=1e-12)


def test_off_grid_interpolation_error(lut):
    rng = np.random.default_rng(1)
    for _ in range(40):
        s, v, r = rng.uniform(21, 49), rng.uniform(0, 12), rng.uniform(30, 180)
        spec = simulate(PARAMS, s, v, r)["rsot"]
        bands = lut.bands_at(s, v, r)
        assert max(abs(bands[w] - spec[w - 400]) for w in INDEX_BANDS) < 1e-3
        assert lut.index_at("NDVI", s, v, r) == pytest.approx(compute_index("NDVI", spec), abs=1e-3)


def test_raa_wrapping_and_broadcasting(lut):
    a = lut.index_at("NDRE", 30.0, 8.0, 300.0)
    b = lut.index_at("NDRE", 30.0, 8.0, 60.0)
    assert a == pytest.approx(b)
    grid = lut.index_at("NDVI", np.array([25.0, 35.0, 45.0]), 4.0, 0.0)
    assert grid.shape == (3,)


def test_out_of_range_raises(lut):
    with pytest.raises(ValueError):
        lut.bands_at(70.0, 0.0, 0.0)


def test_save_load_roundtrip(lut, tmp_path):
    path = tmp_path / "lut.npz"
    lut.save(path)
    back = GeometryLUT.load(path)
    assert back.params == PARAMS and back.factors == lut.factors
    np.testing.assert_array_equal(back.values, lut.values)


def test_cache_reuses_file(tmp_path):
    first = cached_lut(PARAMS, SZA[:3], VZA[:2], RAA[:3], directory=tmp_path)
    assert len(list(tmp_path.glob("lut_*.npz"))) == 1
    second = cached_lut(PARAMS, SZA[:3], VZA[:2], RAA[:3], directory=tmp_path)
    np.testing.assert_array_equal(first.values, second.values)
