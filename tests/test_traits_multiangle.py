"""Checks on trait-error propagation and the multi-angle corrections."""

import numpy as np
import pandas as pd
import pytest

from publication_spectral_data.geometry_scenarios import REFERENCE_GEOMETRY as REF
from publication_spectral_data.indices import compute_index
from publication_spectral_data.multiangle import (
    fit_kernels,
    invert,
    kernel_matrix,
    li_sparse_r,
    normalise_to_reference,
    ross_thick,
    simulate_candidates,
)
from publication_spectral_data.prosail_engine import CanopyParams, simulate
from publication_spectral_data.traits import (
    equivalent_trait,
    fit_trait_model,
    latin_hypercube,
    trait_values,
    training_set,
)

PARAMS = CanopyParams(lai=2.5)


def test_equivalent_trait_is_exact_at_reference():
    vi = compute_index("NDVI", simulate(PARAMS, REF["sza"], REF["vza"], REF["raa"])["rsot"])
    assert equivalent_trait(vi, "NDVI", PARAMS, REF) == pytest.approx(2.5, rel=1e-3)
    assert equivalent_trait(vi, "NDVI", PARAMS, REF, trait="ccc") == pytest.approx(
        trait_values(PARAMS)["ccc"], rel=1e-3)


def test_equivalent_trait_moves_with_geometry():
    vi_low_sun = compute_index("NDVI", simulate(PARAMS, 70, 0, 0)["rsot"])
    assert equivalent_trait(vi_low_sun, "NDVI", PARAMS, REF) > 2.5   # low sun reads as a denser canopy


def test_latin_hypercube_covers_each_range():
    lhs = latin_hypercube(50, {"a": (0.0, 1.0), "b": (10.0, 20.0)}, seed=3)
    for col, (lo, hi) in {"a": (0, 1), "b": (10, 20)}.items():
        assert lhs[col].between(lo, hi).all()
        counts = np.histogram(lhs[col], bins=50, range=(lo, hi))[0]
        assert (counts == 1).all()


def test_trait_model_fits_training_data():
    train = training_set(300, indices=("NDVI",), seed=1)
    model = fit_trait_model(train, "NDVI", "lai")
    assert model.r2 > 0.7
    assert np.isnan(model.predict(model.vi_range[1] + 0.1))


def test_kernels_zero_at_nadir_nadir():
    assert ross_thick(0, 0, 0) == pytest.approx(0, abs=1e-12)
    assert li_sparse_r(0, 0, 0) == pytest.approx(0, abs=1e-12)
    assert li_sparse_r(30, 30, 0) > li_sparse_r(30, 30, 180)   # hotspot brighter than forward


def test_kernel_fit_recovers_weights():
    rng = np.random.default_rng(0)
    sza = np.full(7, 40.0)
    vza = rng.uniform(0, 40, 7)
    raa = rng.uniform(0, 180, 7)
    w = np.array([[0.05, 0.4], [0.02, 0.2], [0.01, 0.03]])
    refl = kernel_matrix(sza, vza, raa) @ w
    np.testing.assert_allclose(fit_kernels(refl, sza, vza, raa), w, atol=1e-10)
    np.testing.assert_allclose(normalise_to_reference(refl, sza, vza, raa, REF),
                               kernel_matrix(45, 0, 0) @ w, atol=1e-10)


def test_inversion_finds_true_candidate():
    cands = latin_hypercube(30, {"lai": (0.5, 6.0), "lidfa": (35, 70)}, seed=2)
    geoms = [(40.0, 0.0, 0.0), (40.0, 20.0, 0.0), (40.0, 20.0, 180.0)]
    refl, traits = simulate_candidates(cands, geoms)
    est = invert(refl[7], refl, traits, n_best=1)
    assert est["lai"] == pytest.approx(cands["lai"].iloc[7])


def test_relative_cost_and_median():
    from publication_spectral_data.multiangle import lut_cost
    obs = np.array([[0.05, 0.40]])
    cands = np.array([[[0.06, 0.40]], [[0.05, 0.41]]])
    rel = lut_cost(obs, cands, relative=True)
    ab = lut_cost(obs, cands, relative=False)
    assert rel[0] > rel[1]            # 20 % error in a dark band costs more than 2.5 % in NIR
    assert ab[0] == pytest.approx(ab[1])


def test_lsq_inversion_recovers_truth_including_hotspot():
    from publication_spectral_data.multiangle import S2_BANDS, invert_lsq
    ranges = {"lai": (0.5, 7.0), "lidfa": (35.0, 70.0), "hspot": (0.005, 0.1)}
    truth = CanopyParams(lai=4.2, lidfa=50.0, hspot=0.04)
    geoms = [(35.0, 0.0, 0.0), (35.0, 20.0, 0.0), (35.0, 20.0, 180.0), (35.0, 35.0, 0.0)]
    obs = np.array([simulate(truth, *g)["rsot"][np.array(S2_BANDS) - 400] for g in geoms])
    cands = latin_hypercube(40, ranges, seed=4)
    refl, _ = simulate_candidates(cands, geoms)
    est = invert_lsq(obs, geoms, refl, cands, ranges, noise_sd=0.02)
    assert est["lai"] == pytest.approx(4.2, rel=0.01)
    assert est["hspot"] == pytest.approx(0.04, rel=0.05)
    assert est["chi2_red"] < 1e-3
