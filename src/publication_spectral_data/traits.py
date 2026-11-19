"""From vegetation-index changes to trait errors (simulation only).

Two levels:

* **Equivalent trait (E3).** For a known canopy, the LAI (or canopy chlorophyll content) that
  would give the observed VI *at the reference geometry*. This is the error that a perfect,
  canopy-specific VI->trait model makes when the geometry changes: pure geometry error.
* **Empirical model (E4).** One VI->trait model fitted on a synthetic training set at the
  reference geometry (as a practitioner would calibrate at one place and time), then applied
  everywhere. Its error mixes geometry error with confounding by the other canopy traits.

Traits:

* ``lai`` -- leaf area index (m2 m-2);
* ``biomass`` -- green leaf dry biomass, LAI x Cm x 1e4 (g m-2);
* ``ccc`` -- canopy chlorophyll content, LAI x Cab x 0.01 (g m-2). It is used as the proxy for
  canopy nitrogen, and so for crude protein. Converting CCC to CP needs a sourced
  chlorophyll-nitrogen relationship. Until one is added, CP errors are reported as CCC errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .indices import compute_index
from .prosail_engine import CanopyParams, simulate

TRAITS = ("lai", "biomass", "ccc")

# Sampling ranges for the synthetic training set. These are a design choice, not measurements:
# they span every canopy used in the scenarios (ryegrass reference and LAI variants; wheat rows
# of data/crop_parameters/growth_stages.csv) with a margin.
TRAINING_RANGES: dict[str, tuple[float, float]] = {
    "lai": (0.2, 7.0),
    "cab": (25.0, 70.0),
    "lidfa": (35.0, 70.0),
    "N": (1.3, 1.9),
    "cm": (0.004, 0.012),
    "cw": (0.008, 0.025),
    "psoil": (0.0, 1.0),
    # Off-nadir views depend on the hotspot size, so multi-angle inversions must estimate it.
    # Range spans the CanopyParams default (0.01) and the sourced wheat values (0.029-0.058).
    "hspot": (0.005, 0.1),
}


def trait_values(params: CanopyParams) -> dict[str, float]:
    return {"lai": params.lai,
            "biomass": params.lai * params.cm * 1e4,
            "ccc": params.lai * params.cab * 0.01}


# --------------------------------------------------------------------------- E3

def equivalent_trait(observed_vi, index: str, params: CanopyParams, reference: Mapping[str, float],
                     trait: str = "lai", factor: str = "rsot",
                     lai_grid: Sequence[float] | None = None) -> np.ndarray:
    """Trait value whose reference-geometry VI equals ``observed_vi``, varying LAI only.

    ``trait`` is ``lai``, ``biomass`` or ``ccc``. All three scale with LAI for a fixed leaf,
    so the inversion runs over LAI and converts. Returns NaN where the VI is outside the
    range the LAI grid reaches, or where the VI-LAI curve is not monotonic.
    """
    lai_grid = np.asarray(lai_grid if lai_grid is not None else np.linspace(0.05, 10.0, 200))
    vis = np.array([compute_index(index, simulate(params.updated(lai=float(l)), reference["sza"],
                                                  reference["vza"], reference["raa"])[factor])
                    for l in lai_grid])
    observed = np.asarray(observed_vi, dtype=float)
    d = np.diff(vis)
    if not (np.all(d > 0) or np.all(d < 0)):
        # keep the monotonic part from the low-LAI end
        sign = np.sign(d[0])
        stop = np.argmax(np.sign(d) != sign) + 1 if np.any(np.sign(d) != sign) else len(vis)
        lai_grid, vis = lai_grid[:stop], vis[:stop]
    order = np.argsort(vis)
    lai = np.interp(observed, vis[order], lai_grid[order], left=np.nan, right=np.nan)
    if trait == "lai":
        return lai
    if trait == "biomass":
        return lai * params.cm * 1e4
    if trait == "ccc":
        return lai * params.cab * 0.01
    raise ValueError(f"trait must be one of {TRAITS}")


# --------------------------------------------------------------------------- E4

def latin_hypercube(n: int, ranges: Mapping[str, tuple[float, float]] = TRAINING_RANGES,
                    seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = {}
    for name, (lo, hi) in ranges.items():
        u = (rng.permutation(n) + rng.random(n)) / n
        cols[name] = lo + u * (hi - lo)
    return pd.DataFrame(cols)


def training_set(n: int = 2000, reference: Mapping[str, float] | None = None,
                 indices: Sequence[str] = ("NDVI", "NDRE", "GNDVI", "EVI", "SAVI", "MTCI"),
                 factor: str = "rsot", base: CanopyParams = CanopyParams(),
                 ranges: Mapping[str, tuple[float, float]] = TRAINING_RANGES,
                 seed: int = 0) -> pd.DataFrame:
    """Random canopies (Latin hypercube) with their traits and VIs at the reference geometry."""
    from .geometry_scenarios import REFERENCE_GEOMETRY
    ref = reference or REFERENCE_GEOMETRY
    samples = latin_hypercube(n, ranges, seed)
    rows = []
    for rec in samples.to_dict("records"):
        params = base.updated(**rec, car=rec.get("cab", base.cab) / 5.0)
        spec = simulate(params, ref["sza"], ref["vza"], ref["raa"])[factor]
        rows.append({**rec, **trait_values(params),
                     **{i: compute_index(i, spec) for i in indices}})
    return pd.DataFrame(rows)


@dataclass(frozen=True)
class TraitModel:
    """log(trait) = cubic polynomial in VI, fitted by least squares."""

    index: str
    trait: str
    coef: np.ndarray
    vi_range: tuple[float, float]
    r2: float
    rmse_rel_pct: float

    def predict(self, vi) -> np.ndarray:
        vi = np.asarray(vi, dtype=float)
        out = np.exp(np.polyval(self.coef, vi))
        lo, hi = self.vi_range
        return np.where((vi >= lo) & (vi <= hi), out, np.nan)


def fit_trait_model(train: pd.DataFrame, index: str, trait: str, degree: int = 3) -> TraitModel:
    x, y = train[index].to_numpy(), train[trait].to_numpy()
    ok = np.isfinite(x) & np.isfinite(y) & (y > 0)
    x, y = x[ok], y[ok]
    coef = np.polyfit(x, np.log(y), degree)
    pred = np.exp(np.polyval(coef, x))
    r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
    rmse_rel = 100 * np.sqrt(np.mean(((pred - y) / y) ** 2))
    return TraitModel(index, trait, coef, (float(x.min()), float(x.max())), float(r2), float(rmse_rel))


def fit_all(train: pd.DataFrame, indices: Sequence[str], traits: Sequence[str] = TRAITS) -> dict:
    return {(i, t): fit_trait_model(train, i, t) for i in indices for t in traits}


def model_table(models: Mapping) -> pd.DataFrame:
    return pd.DataFrame([{"index": m.index, "trait": m.trait, "r2": m.r2,
                          "rmse_rel_pct": m.rmse_rel_pct, "vi_min": m.vi_range[0],
                          "vi_max": m.vi_range[1]} for m in models.values()])
