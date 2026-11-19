"""Multi-angle correction: semi-empirical kernel normalisation and PROSAIL LUT inversion.

Correction A -- **Ross-Thick / Li-Sparse-Reciprocal kernels** (the MODIS BRDF model; Lucht et
al., 2000, IEEE TGRS 38:977). Per band, R = f_iso + f_vol K_vol + f_geo K_geo is fitted to K >= 3
views and evaluated at the reference geometry. When all views share one sun position (one
acquisition), moving to a different solar zenith is an extrapolation in sun angle.

Correction B -- **PROSAIL inversion.** Random canopies are simulated at the actual view
geometries. The best-matching candidates are scored with a noise-weighted (relative) cost
(:func:`invert`), then refined by bounded least squares (:func:`invert_lsq`). With known
geometry, even one view is "geometry-aware". The extra views constrain leaf angle and LAI
separately, because they cannot be told apart at one angle. Off-nadir views also depend on
the hotspot size, so ``hspot`` must be a free parameter.

Angles are in degrees; ``raa = 0`` is the hotspot (backscatter), as in the rest of the project.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .prosail_engine import CanopyParams, simulate, wrap_raa
from .traits import trait_values

# Sentinel-2 MSI band centres (nm) inside the PROSAIL range, used for the inversion.
S2_BANDS = (490, 560, 665, 705, 740, 783, 842, 865, 1610, 2190)


# --------------------------------------------------------------------------- kernels

def ross_thick(sza, vza, raa) -> np.ndarray:
    ts, tv, phi = (np.radians(np.asarray(a, dtype=float)) for a in (sza, vza, wrap_raa(raa)))
    cos_xi = np.clip(np.cos(ts) * np.cos(tv) + np.sin(ts) * np.sin(tv) * np.cos(phi), -1, 1)
    xi = np.arccos(cos_xi)
    return ((np.pi / 2 - xi) * cos_xi + np.sin(xi)) / (np.cos(ts) + np.cos(tv)) - np.pi / 4


def li_sparse_r(sza, vza, raa, h_b: float = 2.0, b_r: float = 1.0) -> np.ndarray:
    ts, tv, phi = (np.radians(np.asarray(a, dtype=float)) for a in (sza, vza, wrap_raa(raa)))
    ts, tv = np.arctan(b_r * np.tan(ts)), np.arctan(b_r * np.tan(tv))
    sec_s, sec_v = 1 / np.cos(ts), 1 / np.cos(tv)
    cos_xi = np.cos(ts) * np.cos(tv) + np.sin(ts) * np.sin(tv) * np.cos(phi)
    d2 = np.tan(ts) ** 2 + np.tan(tv) ** 2 - 2 * np.tan(ts) * np.tan(tv) * np.cos(phi)
    cos_t = h_b * np.sqrt(np.maximum(d2, 0) + (np.tan(ts) * np.tan(tv) * np.sin(phi)) ** 2) / (sec_s + sec_v)
    t = np.arccos(np.clip(cos_t, -1, 1))
    overlap = (t - np.sin(t) * np.cos(t)) * (sec_s + sec_v) / np.pi
    return overlap - sec_s - sec_v + 0.5 * (1 + cos_xi) * sec_s * sec_v


def kernel_matrix(sza, vza, raa) -> np.ndarray:
    """(K, 3) design matrix [1, K_vol, K_geo]."""
    sza, vza, raa = np.broadcast_arrays(*(np.asarray(a, dtype=float) for a in (sza, vza, raa)))
    return np.stack([np.ones(sza.shape), ross_thick(sza, vza, raa), li_sparse_r(sza, vza, raa)], axis=-1)


def fit_kernels(reflectance: np.ndarray, sza, vza, raa) -> np.ndarray:
    """Least-squares kernel weights. ``reflectance`` is (K,) or (K, n_bands); returns (3,) or (3, n_bands)."""
    A = kernel_matrix(sza, vza, raa)
    if A.shape[0] < 3:
        raise ValueError("Kernel fit needs at least 3 views")
    weights, *_ = np.linalg.lstsq(A, np.asarray(reflectance, dtype=float), rcond=None)
    return weights


def kernel_predict(weights: np.ndarray, sza, vza, raa) -> np.ndarray:
    return kernel_matrix(sza, vza, raa) @ weights


def normalise_to_reference(reflectance: np.ndarray, sza, vza, raa,
                           reference: Mapping[str, float]) -> np.ndarray:
    """Kernel-fit the views and return reflectance at the reference geometry."""
    w = fit_kernels(reflectance, sza, vza, raa)
    return kernel_predict(w, reference["sza"], reference["vza"], reference["raa"])


# --------------------------------------------------------------------------- LUT inversion

def simulate_candidates(candidates: pd.DataFrame, geometries: Sequence[tuple[float, float, float]],
                        base: CanopyParams = CanopyParams(), bands: Sequence[int] = S2_BANDS,
                        factor: str = "rsot") -> tuple[np.ndarray, pd.DataFrame]:
    """Reflectance (n, K, n_bands) of each candidate canopy at each (sza, vza, raa), plus traits."""
    idx = np.asarray(bands) - 400
    refl = np.empty((len(candidates), len(geometries), len(bands)))
    traits = []
    for n, rec in enumerate(candidates.to_dict("records")):
        params = base.updated(**rec, car=rec.get("cab", base.cab) / 5.0)
        traits.append({**rec, **trait_values(params)})
        for k, (s, v, r) in enumerate(geometries):
            refl[n, k] = simulate(params, s, v, r)[factor][idx]
    return refl, pd.DataFrame(traits)


def lut_cost(observed: np.ndarray, candidate_refl: np.ndarray, views: Sequence[int] | None = None,
             relative: bool = True) -> np.ndarray:
    """RMSE of each candidate over the chosen views and bands.

    ``relative=True`` divides residuals by the observation. That is the maximum-likelihood
    weighting for multiplicative noise, and it stops the bright NIR bands from dominating.
    """
    observed = np.asarray(observed)
    views = list(views) if views is not None else list(range(observed.shape[0]))
    diff = candidate_refl[:, views, :] - observed[views][None]
    if relative:
        diff = diff / observed[views][None]
    return np.sqrt(np.mean(diff ** 2, axis=(1, 2)))


def invert(observed: np.ndarray, candidate_refl: np.ndarray, candidate_traits: pd.DataFrame,
           views: Sequence[int] | None = None, n_best: int = 20, relative: bool = True,
           statistic: str = "median") -> pd.Series:
    """Traits of the ``n_best`` lowest-cost candidates (median by default; see :func:`lut_cost`).

    ``observed`` is (K, n_bands); ``views`` picks a subset of the K geometries (default all).
    """
    cost = lut_cost(observed, candidate_refl, views, relative)
    best = candidate_traits.iloc[np.argsort(cost)[:n_best]]
    return best.median(numeric_only=True) if statistic == "median" else best.mean(numeric_only=True)


def invert_lsq(observed: np.ndarray, geometries: Sequence[tuple[float, float, float]],
               candidate_refl: np.ndarray, candidates: pd.DataFrame,
               ranges: Mapping[str, tuple[float, float]],
               views: Sequence[int] | None = None, noise_sd: float = 0.02, n_starts: int = 2,
               base: CanopyParams = CanopyParams(), bands: Sequence[int] = S2_BANDS,
               factor: str = "rsot", max_nfev: int = 200) -> pd.Series:
    """Bounded least-squares refinement of the LUT inversion.

    Starts from the ``n_starts`` lowest-cost LUT candidates and minimises the noise-weighted
    residuals (sim - obs) / (noise_sd * obs) over the chosen views and bands, with every
    parameter in ``ranges`` free within its bounds. Returns traits, parameters, the final
    reduced chi-square, and ``at_bound`` (names of parameters that ended on a bound).
    """
    from scipy.optimize import least_squares

    observed = np.asarray(observed)
    views = list(views) if views is not None else list(range(observed.shape[0]))
    geoms = [geometries[i] for i in views]
    obs = observed[views]
    names = list(ranges)
    lo = np.array([ranges[n][0] for n in names])
    hi = np.array([ranges[n][1] for n in names])
    idx = np.asarray(bands) - 400
    sd = max(noise_sd, 1e-3)

    def params_of(x):
        rec = dict(zip(names, lo + np.clip(x, 0, 1) * (hi - lo)))
        return base.updated(**rec, car=rec.get("cab", base.cab) / 5.0)

    def residuals(x):
        p = params_of(x)
        sim = np.array([simulate(p, *g)[factor][idx] for g in geoms])
        return ((sim - obs) / (sd * obs)).ravel()

    cost = lut_cost(observed, candidate_refl, views)
    best = None
    for start in np.argsort(cost)[:n_starts]:
        x0 = (candidates.iloc[start][names].to_numpy(dtype=float) - lo) / (hi - lo)
        res = least_squares(residuals, np.clip(x0, 1e-6, 1 - 1e-6), bounds=(0, 1),
                            diff_step=1e-3, max_nfev=max_nfev)
        if best is None or res.cost < best.cost:
            best = res
    params = params_of(best.x)
    dof = max(obs.size - len(names), 1)
    at_bound = [n for n, x in zip(names, best.x) if x < 1e-4 or x > 1 - 1e-4]
    return pd.Series({**{n: getattr(params, n) for n in names}, **trait_values(params),
                      "chi2_red": 2 * best.cost / dof, "nfev": best.nfev,
                      "at_bound": ",".join(at_bound)})


def add_noise(reflectance: np.ndarray, relative_sd: float, rng: np.random.Generator) -> np.ndarray:
    """Multiplicative Gaussian radiometric noise."""
    return reflectance * (1 + relative_sd * rng.standard_normal(np.shape(reflectance)))
