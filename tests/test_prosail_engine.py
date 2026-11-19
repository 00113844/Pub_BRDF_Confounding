"""Checks on the patched PyProSAIL build and the shared PROSAIL engine."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

import pyprosail
from publication_spectral_data.crop_params import stage_params
from publication_spectral_data.indices import compute_index
from publication_spectral_data.prosail_engine import (
    FACTORS,
    CanopyParams,
    brdf_grid,
    builtin_soils,
    simulate,
    wrap_raa,
)
from publication_spectral_data.solar import relative_azimuth, solar_position

BASE = dict(n=1.5, cab=40, car=8, cbrown=0, cw=0.01, cm=0.009, psoil=0.5, lai=2.5,
            hspot=0.05, tts=30, tto=10, psi=0, typelidf=2, lidfa=60, lidfb=0)


def run(**changes):
    return pyprosail.run_all(**{**BASE, **changes})


def test_outputs_have_full_spectral_range():
    res = run()
    assert res.wavelength[0] == 400 and res.wavelength[-1] == 2500
    for factor in FACTORS:
        spectrum = getattr(res, factor)
        assert spectrum.shape == (2101,)
        assert np.all(np.isfinite(spectrum))
        assert np.all((spectrum > 0) & (spectrum < 1))


def test_upstream_run_returns_wavelength_and_resv():
    arr = pyprosail.run(*BASE.values())
    assert arr.shape == (2101, 2)
    np.testing.assert_array_equal(arr[:, 1], run().resv)


@pytest.mark.parametrize("psi, equivalent", [(350, 10), (-30, 30), (540, 180), (190, 170)])
def test_psi_is_wrapped(psi, equivalent):
    a = run(tts=40, tto=60, psi=psi).rsot
    b = run(tts=40, tto=60, psi=equivalent).rsot
    np.testing.assert_allclose(a, b, rtol=0, atol=1e-12)


@pytest.mark.parametrize("bad", [
    dict(typelidf=1, lidfa=0.5, lidfb=-0.8),   # passed upstream's lidfa + lidfb check
    dict(typelidf=3),
    dict(typelidf=2, lidfa=95),
    dict(tts=90),
    dict(tto=90),
    dict(psoil=1.2),
    dict(lai=-1),
    dict(n=0.5),
    dict(cab=float("nan")),
])
def test_invalid_inputs_raise(bad):
    with pytest.raises(ValueError):
        run(**bad)


def test_hotspot_peak_is_at_solar_direction():
    # BRF in the principal plane on the sun's side peaks where vza == sza
    vza = np.arange(0, 61, 2)
    nir = [run(tto=v, psi=0).rsot[800 - 400] for v in vza]
    assert vza[int(np.argmax(nir))] == BASE["tts"]


def test_resv_is_a_mix_of_direct_and_diffuse():
    res = run()
    low = np.minimum(res.rdot, res.rsot) - 1e-12
    high = np.maximum(res.rdot, res.rsot) + 1e-12
    assert np.all((res.resv >= low) & (res.resv <= high))


def test_custom_soil_spectrum_matches_builtin_mix():
    dry, wet = builtin_soils()
    mixed = 0.3 * dry + 0.7 * wet
    np.testing.assert_allclose(run(psoil=0.3).rsot, run(soil_spectrum=mixed).rsot, atol=1e-12)


def test_zero_lai_returns_soil():
    dry, _ = builtin_soils()
    np.testing.assert_allclose(run(lai=0, psoil=1).rsot, dry)


def test_soil_scale_darkens_sparse_canopy():
    p = CanopyParams(lai=0.5)
    bright = simulate(p, 30, 0, 0)["rsot"][670 - 400]
    dark = simulate(p.updated(soil_scale=0.5), 30, 0, 0)["rsot"][670 - 400]
    assert dark < bright


def test_engine_rejects_near_horizontal_view():
    with pytest.raises(ValueError):
        simulate(CanopyParams(), 30, 89, 0)


def test_backends_agree():
    pytest.importorskip("prosail")
    for sza, vza, raa in [(30, 0, 0), (45, 30, 0), (45, 30, 180), (60, 70, 90)]:
        a = simulate(CanopyParams(), sza, vza, raa, backend="pyprosail")
        b = simulate(CanopyParams(), sza, vza, raa, backend="prosail_py")
        for factor in FACTORS:
            np.testing.assert_allclose(a[factor], b[factor], atol=2e-3, err_msg=factor)


def test_brdf_grid_is_symmetric_about_principal_plane():
    grid = brdf_grid(CanopyParams(), 30, [20, 50], [30, 330], factor="rsot", index="NDVI")
    pivot = grid.pivot(index="vza", columns="raa", values="value")
    np.testing.assert_allclose(pivot[30.0], pivot[330.0])


def test_wrap_raa():
    assert wrap_raa(350) == pytest.approx(10)
    np.testing.assert_allclose(wrap_raa([0, 180, 270, -90, 720]), [0, 180, 90, 90, 0])


def test_ndvi_of_vegetation_is_high():
    assert 0.6 < compute_index("NDVI", simulate(CanopyParams(), 30, 0, 0)["rsot"]) < 1


def test_solar_position_perth_summer_noon():
    pos = solar_position(-31.95, 115.86, datetime(2026, 12, 21, 12, 30))
    assert pos.timezone == "Australia/Perth"
    assert 5 < pos.sza < 15          # sun near zenith at the southern summer solstice
    assert relative_azimuth(pos.saa, pos.saa) == 0


def test_stage_params_falls_back_to_defaults():
    row = pd.Series({"crop": "wheat", "zadoks": 30, "lai_min": 1.0, "lai_typ": 2.0,
                     "lai_max": 3.0, "cab": 45.0, "lidfa": float("nan")})
    params, defaulted = stage_params(row, "lai_max")
    assert params.lai == 3.0 and params.cab == 45.0
    assert params.lidfa == CanopyParams().lidfa
    assert "lidfa" in defaulted and "cab" not in defaulted
