"""BRDF polar grids for the paper figures: tidy CSV (canopy, quantity, factor, sza, vza, raa, value).

Canopies: ryegrass_ref, ryegrass_lai1.0, wheat_Z30, wheat_Z55 (run_australia_scenarios.canopies()).
SZA 30, 45, 60 deg; VZA 0-60 step 2; RAA 0-360 step 5 (wrapped to [0, 180] by the engine; raa = 0
hotspot). Quantities: R670, R800 reflectance factors and NDVI, NDRE, for rsot (BRF) and resv
(sun + sky). Also the reference values at nadir / SZA 45 deg.
Usage (from ~/brdf): NPROC=8 uv run python scripts/brdf_polar_grids.py out.csv
"""
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import run_australia_scenarios as ras  # noqa: E402
from publication_spectral_data.indices import compute_index  # noqa: E402
from publication_spectral_data.prosail_engine import simulate, wrap_raa  # noqa: E402

CANOPIES = ["ryegrass_ref", "ryegrass_lai1.0", "wheat_Z30", "wheat_Z55"]
SZAS = [30.0, 45.0, 60.0]
VZA = np.arange(0.0, 61.0, 2.0)
RAA = np.arange(0.0, 361.0, 5.0)


def task(args):
    canopy, sza = args
    params = ras.canopies()[canopy]
    cache, rows = {}, []
    for v in VZA:
        for a in RAA:
            key = (v, round(float(wrap_raa(a)), 6))
            if key not in cache:
                s = simulate(params, sza, v, a)
                cache[key] = {f: {"R670": float(s[f][270]), "R800": float(s[f][400]),
                                  "NDVI": float(compute_index("NDVI", s[f])),
                                  "NDRE": float(compute_index("NDRE", s[f]))} for f in ("rsot", "resv")}
            for f, q in cache[key].items():
                for name, val in q.items():
                    rows.append((canopy, name, f, sza, v, a, val))
    return rows


def main(out):
    with Pool(int(os.environ.get("NPROC", 8))) as pool:
        parts = pool.map(task, [(c, s) for c in CANOPIES for s in SZAS])
    df = pd.DataFrame([r for p in parts for r in p], columns=["canopy", "quantity", "factor", "sza", "vza", "raa", "value"])
    ref = []
    for c in CANOPIES:
        s = simulate(ras.canopies()[c], 45.0, 0.0, 0.0)
        for f in ("rsot", "resv"):
            ref += [(c, "NDVI", f, float(compute_index("NDVI", s[f]))), (c, "NDRE", f, float(compute_index("NDRE", s[f]))),
                    (c, "R670", f, float(s[f][270])), (c, "R800", f, float(s[f][400]))]
    df.to_csv(out, index=False)
    pd.DataFrame(ref, columns=["canopy", "quantity", "factor", "ref_value"]).to_csv(out.replace(".csv", "_ref.csv"), index=False)
    print(len(df), "rows")


if __name__ == "__main__":
    main(sys.argv[1])
