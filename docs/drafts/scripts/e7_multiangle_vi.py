"""E7: multi-angle vegetation-index combinations for LAI that are insensitive to geometry.

Target trait: LAI only. Reflectance factor: rsot (BRF, direct sun). Noise: 2 % multiplicative on
every band and view (as E5). Views: E5_VIEWS (vza, raa relative to the sun) and view sets E5_SETS
(K = 1, 3, 5, 9).

Features for a subset S of the six indices (NDVI, NDRE, GNDVI, EVI, SAVI, MTCI; singles and pairs):
  view  : each index at each view of the set (|S| x K)
  mean  : angular mean of each index over the set (|S|)                       (K >= 3)
  aniso : angular mean + backscatter/forward normalised difference of each index for the
          principal-plane pairs present in the set ((20,0)-(20,180); (35,0)-(35,180))  (K >= 3)
Model: ln(LAI) = ridge regression on standardised quadratic polynomial features (RidgeCV).

Calibration modes:
  naive    : trained at the reference geometry only (SZA 45 deg), no sun-angle input;
             "calibrate once, apply everywhere".
  pooled   : trained over sun positions sampled from the handheld/UAV geometry of all 19 sites,
             12 months, 09:00-15:00 local clock time (SZA <= 75 deg); no sun-angle input.
  geoaware : as pooled, plus cos(SZA) of the measurement as an input (the sun position is known
             at measurement time).

Training canopies: Latin hypercube over traits.TRAINING_RANGES, seed TRAIN_SEED (independent of the
test truths). Test: the 50 independent truths of e5_robustness.py (seed 20261111) plus the 4 named
E5 canopies, 24 sun positions (6 highlight sites x Jan/Apr/Jul/Oct, UAV 11:00), 5 noise repeats.
Location spread = p95 - p05 of the 24 site-month mean errors of one canopy, median over the 50
independent canopies (as E5 robustness).

Usage (from ~/brdf):  NPROC=8 uv run --with scikit-learn python scripts/e7_multiangle_vi.py --out results/e7
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time as _time
from datetime import date, time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import run_australia_scenarios as ras  # noqa: E402
from publication_spectral_data.geometry_scenarios import handheld_geometry, load_sites, monthly_dates  # noqa: E402
from publication_spectral_data.indices import INDEX_BANDS, compute_index  # noqa: E402
from publication_spectral_data.multiangle import add_noise  # noqa: E402
from publication_spectral_data.prosail_engine import CanopyParams, simulate  # noqa: E402
from publication_spectral_data.traits import TRAINING_RANGES, latin_hypercube, trait_values  # noqa: E402

NPROC = int(os.environ.get("NPROC", os.cpu_count() or 1))
VIS = ("NDVI", "NDRE", "GNDVI", "EVI", "SAVI", "MTCI")
VIEWS = ras.E5_VIEWS
SETS = ras.E5_SETS
NOISE = ras.E5_NOISE
TRUTH_SEED = 20261111
TRAIN_SEED = 424242
N_TRAIN = 1500
SUNS_PER_TRAIN = 6
REPS = 5
PAIRS = [((20, 0), (20, 180)), ((35, 0), (35, 180))]
REF_SZA = 45.0


# ----------------------------------------------------------------------------- simulation

def _vis_for(params, sza, rng):
    """(9 views, 6 indices) noisy VI matrix for one canopy and sun zenith."""
    bands = np.array([[simulate(params, sza, v, r)["rsot"][w - 400] for w in INDEX_BANDS] for v, r in VIEWS])
    obs = add_noise(bands, NOISE, rng)
    return np.array([[float(compute_index(n, dict(zip(INDEX_BANDS, row)))) for n in VIS] for row in obs])


def _train_task(args):
    j, rec, szas, seed = args
    params = CanopyParams().updated(**rec, car=rec["cab"] / 5.0)
    rng = np.random.default_rng(seed)
    lai = trait_values(params)["lai"]
    return [(j, s, lai, _vis_for(params, s, rng)) for s in szas]


def _test_task(args):
    name, params, sun_i, sza, site, month, seed = args
    rng = np.random.default_rng(seed)
    lai = trait_values(params)["lai"]
    return [(name, sun_i, site, month, sza, rep, lai, _vis_for(params, sza, rng)) for rep in range(REPS)]


def training_data(mode_pool_szas, pool_rng):
    lhs = latin_hypercube(N_TRAIN, TRAINING_RANGES, seed=TRAIN_SEED).to_dict("records")
    tasks_pooled = [(j, rec, list(pool_rng.choice(mode_pool_szas, SUNS_PER_TRAIN, replace=False)), 7_000_000 + j)
                    for j, rec in enumerate(lhs)]
    tasks_naive = [(j, rec, [REF_SZA], 8_000_000 + j) for j, rec in enumerate(lhs)]
    with Pool(NPROC) as pool:
        pooled = [r for part in pool.imap(_train_task, tasks_pooled, chunksize=16) for r in part]
        naive = [r for part in pool.imap(_train_task, tasks_naive, chunksize=16) for r in part]
    def pack(rows):
        return (np.array([r[1] for r in rows]), np.array([r[2] for r in rows]), np.stack([r[3] for r in rows]))
    return {"naive": pack(naive), "pooled": pack(pooled)}


def test_data():
    base = CanopyParams()
    truths = {}
    for j, rec in enumerate(latin_hypercube(50, TRAINING_RANGES, seed=TRUTH_SEED).to_dict("records")):
        truths[f"lhs_{j:02d}"] = ("independent_lhs", base.updated(**rec, car=rec["cab"] / 5.0))
    named = ras.canopies()
    for n in ras.E5_CANOPIES:
        truths[n] = ("named_e5", named[n])
    sites = load_sites()
    sites = sites[sites["site"].isin(ras.HIGHLIGHT_SITES)]
    sun = handheld_geometry(sites, [date(2026, m, 15) for m in ras.MAP_MONTHS], [ras.UAV_TIME])
    sun = [{"site": r.site, "month": pd.Timestamp(r.time_local).month, "sza": float(r.sza)}
           for r in sun.itertuples(index=False)]
    tasks = []
    for t_i, (name, (_, params)) in enumerate(truths.items()):
        for i, s in enumerate(sun):
            tasks.append((name, params, i, s["sza"], s["site"], s["month"], 9_000_000 + 1000 * i + t_i))
    with Pool(NPROC) as pool:
        rows = [r for part in pool.imap(_test_task, tasks, chunksize=8) for r in part]
    meta = pd.DataFrame([{"canopy": r[0], "sun": r[1], "site": r[2], "month": r[3], "sza": r[4], "rep": r[5],
                          "truth_lai": r[6], "truth_set": truths[r[0]][0]} for r in rows])
    return meta, np.stack([r[7] for r in rows]), sun


# ----------------------------------------------------------------------------- features & models

def features(V, sza, subset, K, family, geoaware):
    """V: (n, 9 views, 6 VIs). Returns (n, p) feature matrix."""
    vidx = SETS[K]
    cols = [VIS.index(s) for s in subset]
    X = []
    if family == "view":
        for c in cols:
            for v in vidx:
                X.append(V[:, v, c])
    else:
        for c in cols:
            X.append(V[:, vidx, c].mean(axis=1))
        if family == "aniso":
            present = [VIEWS.index(p) for p in [q for pair in PAIRS for q in pair]]
            for back, fwd in PAIRS:
                b, f = VIEWS.index(back), VIEWS.index(fwd)
                if b in vidx and f in vidx:
                    for c in cols:
                        X.append((V[:, b, c] - V[:, f, c]) / (V[:, b, c] + V[:, f, c]))
    if geoaware:
        X.append(np.cos(np.radians(sza)))
    return np.column_stack(X)


def model_specs():
    subsets = [(s,) for s in VIS] + list(itertools.combinations(VIS, 2))
    specs = []
    for K in SETS:
        fams = ["view"] if K == 1 else ["view", "mean", "aniso"]
        for fam in fams:
            for sub in subsets:
                for mode in ("naive", "pooled", "geoaware"):
                    specs.append((K, fam, sub, mode))
    return specs


TR: dict = {}
TE: dict = {}


def _fit_eval(spec):
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler
    K, fam, sub, mode = spec
    src = "naive" if mode == "naive" else "pooled"
    szas, lai, V = TR[src]
    geo = mode == "geoaware"
    Xtr = features(V, szas, sub, K, fam, geo)
    ok = np.all(np.isfinite(Xtr), axis=1)
    model = make_pipeline(StandardScaler(), PolynomialFeatures(2, include_bias=False), StandardScaler(),
                          RidgeCV(alphas=np.logspace(-4, 3, 15)))
    model.fit(Xtr[ok], np.log(lai[ok]))
    meta, Vte = TE["meta"], TE["V"]
    Xte = features(Vte, meta["sza"].to_numpy(), sub, K, fam, geo)
    okt = np.all(np.isfinite(Xte), axis=1)
    pred = np.full(len(meta), np.nan)
    # clip to the training log-LAI range to avoid polynomial blow-up outside the calibration domain
    lo, hi = np.log(lai[ok]).min(), np.log(lai[ok]).max()
    pred[okt] = np.exp(np.clip(model.predict(Xte[okt]), lo - 0.5, hi + 0.5))
    err = 100 * (pred - meta["truth_lai"].to_numpy()) / meta["truth_lai"].to_numpy()
    df = meta.assign(err_pct=err)
    ind = df[df["truth_set"] == "independent_lhs"]
    sm = ind.groupby(["canopy", "site", "month"])["err_pct"].mean()
    spread = sm.groupby("canopy").agg(lambda x: x.quantile(0.95) - x.quantile(0.05))
    return {"K": K, "family": fam, "indices": "+".join(sub), "n_indices": len(sub), "mode": mode,
            "n_features": Xtr.shape[1], "alpha": float(model[-1].alpha_),
            "train_r2": float(model.score(Xtr[ok], np.log(lai[ok]))),
            "mae_pct": float(np.nanmean(np.abs(ind["err_pct"]))),
            "bias_pct": float(np.nanmean(ind["err_pct"])),
            "p95_abs_pct": float(np.nanpercentile(np.abs(ind["err_pct"]), 95)),
            "spread_median_pct": float(spread.median()), "spread_mean_pct": float(spread.mean()),
            "frac_nan": float(np.mean(~np.isfinite(ind["err_pct"]))),
            "named_mae_pct": float(np.nanmean(np.abs(df[df["truth_set"] == "named_e5"]["err_pct"])))}, \
        (spec, spread.to_dict(), df["err_pct"].to_numpy())


def pareto(df, x="mae_pct", y="spread_median_pct"):
    d = df.sort_values([x, y]).reset_index(drop=True)
    keep, best = [], np.inf
    for i, r in d.iterrows():
        if r[y] < best - 1e-12:
            keep.append(i)
            best = r[y]
    return d.loc[keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/e7")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = _time.time()
    sites = load_sites()
    pool_geo = handheld_geometry(sites, monthly_dates(), [time(h, 0) for h in range(9, 16)])
    pool_szas = pool_geo["sza"].to_numpy()
    pool_szas = pool_szas[pool_szas <= 75.0]
    TR.update(training_data(pool_szas, np.random.default_rng(TRAIN_SEED)))
    print(f"  training sims done {time_s(t0)}; pooled n={len(TR['pooled'][1])}, naive n={len(TR['naive'][1])}", flush=True)
    meta, Vte, sun = test_data()
    TE.update(meta=meta, V=Vte)
    print(f"  test sims done {time_s(t0)}; n={len(meta)}", flush=True)
    specs = model_specs()
    with Pool(NPROC) as pool:
        res = pool.map(_fit_eval, specs, chunksize=4)
    summ = pd.DataFrame([r[0] for r in res])
    summ.to_csv(out / "e7_models.csv", index=False)
    # per-canopy spreads and per-sample errors for the Pareto models (for CIs / figures)
    par = pd.concat([pareto(summ[summ["mode"] == m]).assign(front=m) for m in ("naive", "pooled", "geoaware")]
                    + [pareto(summ).assign(front="all")], ignore_index=True)
    par.to_csv(out / "e7_pareto.csv", index=False)
    keyset = {(r.K, r.family, tuple(r.indices.split("+")), r.mode) for r in par.itertuples()}
    best = summ.loc[summ.groupby(["K", "mode"])["mae_pct"].idxmin()]
    keyset |= {(r.K, r.family, tuple(r.indices.split("+")), r.mode) for r in best.itertuples()}
    rows = []
    for (spec, spread, err) in [r[1] for r in res]:
        if spec in keyset:
            K, fam, sub, mode = spec
            for can, s in spread.items():
                rows.append({"K": K, "family": fam, "indices": "+".join(sub), "mode": mode, "canopy": can, "spread_pct": s})
    pd.DataFrame(rows).to_csv(out / "e7_selected_canopy_spread.csv", index=False)
    best.to_csv(out / "e7_best_by_K_mode.csv", index=False)
    meta.drop(columns=[]).to_csv(out / "e7_test_meta.csv", index=False)
    json.dump({"n_models": len(specs), "n_train_pooled": int(len(TR["pooled"][1])), "n_train_naive": int(len(TR["naive"][1])),
               "n_test": int(len(meta)), "pool_sza_range": [float(pool_szas.min()), float(pool_szas.max())],
               "test_sza_range": [float(meta["sza"].min()), float(meta["sza"].max())], "nproc": NPROC,
               "wall_s": round(_time.time() - t0, 1)}, open(out / "e7_meta.json", "w"), indent=2)
    print(f"  done {time_s(t0)}; {len(specs)} models", flush=True)


def time_s(t0):
    return f"{_time.time() - t0:.0f} s"


if __name__ == "__main__":
    main()
