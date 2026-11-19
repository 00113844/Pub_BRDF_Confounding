"""Cross-check PROSAIL implementations.

Compares, on a shared matrix of canopies and sun/view geometries:
  * pyprosail   -- patched PyProSAIL Fortran (project engine)
  * prosail_py  -- jgomezdans pure-Python prosail (PROSPECT-5 + 4SAIL)
  * R prosail   -- jbferet R package (PROSPECT-PRO + 4SAIL), if
                   results/logs/crosscheck_r_spectra.csv exists
                   (run scripts/crosscheck_prosail.R after the first pass of this script)

It also measures the relative-azimuth (psi) wrapping bug in the unpatched code
paths, and the difference between the sun + sky output (resv) and the BRF (rsot).

Usage:  uv run python scripts/crosscheck_prosail.py
Outputs: results/logs/crosscheck_*.csv and results/figures/crosscheck_*.png
"""

from __future__ import annotations

import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import prosail  # jgomezdans; installed with the dev dependency group

from publication_spectral_data.prosail_engine import (
    FACTORS,
    WAVELENGTHS,
    CanopyParams,
    builtin_soils,
    simulate,
)

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "results" / "logs"
FIGURES = ROOT / "results" / "figures"

CANOPIES = {
    "ryegrass_default": CanopyParams(),
    "sparse_erect": CanopyParams(lai=0.8, lidfa=70.0, cab=30.0),
    "dense_planophile": CanopyParams(lai=5.0, lidfa=30.0, cab=55.0, hspot=0.1),
}
SZA = (20.0, 45.0, 60.0)
VZA = (0.0, 20.0, 40.0, 60.0, 80.0)
RAA = (0.0, 90.0, 180.0)

REGIONS = {
    "VIS 400-700": (400, 700),
    "red-edge 700-750": (700, 750),
    "NIR 750-1300": (750, 1300),
    "SWIR 1300-2500": (1300, 2501),
}
R_STEP_NM = 10  # the R script writes spectra every 10 nm to keep the file small


def region_stats(diff: np.ndarray, wavelengths: np.ndarray) -> dict[str, float]:
    out = {}
    for name, (lo, hi) in REGIONS.items():
        d = diff[(wavelengths >= lo) & (wavelengths < hi)]
        out[f"max_abs {name}"] = float(np.max(np.abs(d)))
        out[f"rmsd {name}"] = float(np.sqrt(np.mean(d ** 2)))
    return out


def case_table() -> pd.DataFrame:
    rows = []
    for (name, p), sza, vza, raa in itertools.product(CANOPIES.items(), SZA, VZA, RAA):
        rows.append({"case_id": len(rows), "canopy": name, "sza": sza, "vza": vza, "raa": raa,
                     **p.to_dict()})
    return pd.DataFrame(rows)


def compare_python_backends(cases: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for case in cases.itertuples():
        p = CANOPIES[case.canopy]
        a = simulate(p, case.sza, case.vza, case.raa, backend="pyprosail")
        b = simulate(p, case.sza, case.vza, case.raa, backend="prosail_py")
        for factor in FACTORS:
            rows.append({"case_id": case.case_id, "canopy": case.canopy, "sza": case.sza,
                         "vza": case.vza, "raa": case.raa, "factor": factor,
                         "comparison": "pyprosail - prosail_py",
                         **region_stats(a[factor] - b[factor], WAVELENGTHS)})
    return pd.DataFrame(rows)


def compare_r(cases: pd.DataFrame) -> pd.DataFrame | None:
    path = LOGS / "crosscheck_r_spectra.csv"
    if not path.exists():
        print(f"  {path.name} not found; run scripts/crosscheck_prosail.R to add the R comparison")
        return None
    r = pd.read_csv(path)
    rows = []
    for (case_id, factor), grp in r.groupby(["case_id", "factor"]):
        case = cases.loc[cases.case_id == case_id].iloc[0]
        a = simulate(CANOPIES[case.canopy], case.sza, case.vza, case.raa)[factor]
        wl = grp["wavelength"].to_numpy()
        rows.append({"case_id": case_id, "canopy": case.canopy, "sza": case.sza, "vza": case.vza,
                     "raa": case.raa, "factor": factor, "comparison": "pyprosail - R prosail",
                     **region_stats(a[wl - 400] - grp["value"].to_numpy(), wl)})
    return pd.DataFrame(rows)


def psi_wrap_effect() -> pd.DataFrame:
    """Unwrapped psi in the unpatched code: compare raa and 360 - raa (should be identical)."""
    p = CANOPIES["ryegrass_default"]
    rows = []
    for sza, vza, raa in itertools.product((30.0, 45.0), (20.0, 40.0, 60.0), (10.0, 30.0, 60.0, 120.0)):
        def raw(psi):
            # Direct call to jgomezdans prosail, which (like upstream PyProSAIL) does not wrap psi
            return prosail.run_prosail(p.N, p.cab, p.car, p.cbrown, p.cw, p.cm, p.lai, p.lidfa,
                                       p.hspot, tts=sza, tto=vza, psi=psi, typelidf=2,
                                       prospect_version="5", factor="SDR", rsoil=1.0,
                                       psoil=p.psoil)
        a, b = raw(raa), raw(360.0 - raa)
        for wl in (670, 800):
            rows.append({"sza": sza, "vza": vza, "raa": raa, "mirror_raa": 360.0 - raa,
                         "wavelength": wl, "rsot_raa": a[wl - 400], "rsot_mirror": b[wl - 400],
                         "relative_error_pct": 100.0 * (b[wl - 400] - a[wl - 400]) / a[wl - 400]})
    return pd.DataFrame(rows)


def resv_vs_rsot() -> pd.DataFrame:
    """How much the sun + sky output damps the BRF anisotropy (principal plane)."""
    p = CANOPIES["ryegrass_default"]
    rows = []
    for sza in SZA:
        for wl in (480, 670, 800, 1650):
            sims = {raa: simulate(p, sza, sza, raa) for raa in (0.0, 180.0)}
            nadir = simulate(p, sza, 0.0, 0.0)
            for factor in ("rsot", "resv"):
                hot = sims[0.0][factor][wl - 400]
                fwd = sims[180.0][factor][wl - 400]
                rows.append({"sza": sza, "wavelength": wl, "factor": factor,
                             "nadir": nadir[factor][wl - 400], "hotspot": hot,
                             "forward_at_same_vza": fwd,
                             "hotspot_to_forward_ratio": hot / fwd})
    return pd.DataFrame(rows)


def summarise(diffs: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in diffs.columns if c.startswith(("max_abs", "rmsd"))]
    agg = {c: ("max" if c.startswith("max_abs") else "mean") for c in cols}
    return diffs.groupby(["comparison", "factor"]).agg(agg).reset_index()


def plot_spectra(cases: pd.DataFrame) -> None:
    case = cases[(cases.canopy == "ryegrass_default") & (cases.sza == 45) & (cases.vza == 20)
                 & (cases.raa == 0)].iloc[0]
    p = CANOPIES[case.canopy]
    a = simulate(p, case.sza, case.vza, case.raa)
    b = simulate(p, case.sza, case.vza, case.raa, backend="prosail_py")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(WAVELENGTHS, a["rsot"], label="pyprosail rsot (BRF)", color="#1b7837")
    ax1.plot(WAVELENGTHS, a["resv"], label="pyprosail resv (sun + sky)", color="#762a83")
    ax2.plot(WAVELENGTHS, a["rsot"] - b["rsot"], label="pyprosail - prosail_py", color="#1b7837")
    r_path = LOGS / "crosscheck_r_spectra.csv"
    if r_path.exists():
        r = pd.read_csv(r_path)
        r = r[(r.case_id == case.case_id) & (r.factor == "rsot")]
        ax1.plot(r.wavelength, r.value, "--", label="R prosail rsot (PROSPECT-PRO)", color="#e08214")
        ax2.plot(r.wavelength, a["rsot"][r.wavelength.to_numpy() - 400] - r.value.to_numpy(),
                 label="pyprosail - R prosail", color="#e08214")
    ax1.set_ylabel("Reflectance factor")
    ax1.set_title(f"Ryegrass default canopy, SZA {case.sza:g}°, VZA {case.vza:g}°, RAA {case.raa:g}°")
    ax1.legend(frameon=False)
    ax2.axhline(0, color="grey", lw=0.8)
    ax2.set_xlabel("Wavelength (nm)")
    ax2.set_ylabel("Difference")
    ax2.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "crosscheck_spectra.png", dpi=200)
    plt.close(fig)


def plot_psi_bug() -> None:
    p = CANOPIES["ryegrass_default"]
    sza, vza = 45.0, 60.0
    raa = np.arange(0, 361, 5)
    raw = [prosail.run_prosail(p.N, p.cab, p.car, p.cbrown, p.cw, p.cm, p.lai, p.lidfa, p.hspot,
                               tts=sza, tto=vza, psi=r, typelidf=2, prospect_version="5",
                               factor="SDR", rsoil=1.0, psoil=p.psoil)[400] for r in raa]
    fixed = [simulate(p, sza, vza, r)["rsot"][400] for r in raa]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(raa, fixed, label="pyprosail, raa wrapped to [0, 180] (patched)", color="#1b7837")
    ax.plot(raa, raw, "--", label="jgomezdans prosail, raa passed unwrapped (as upstream PyProSAIL)", color="#b2182b")
    ax.set_xlabel("Relative azimuth (°)")
    ax.set_ylabel("BRF at 800 nm")
    ax.set_title(f"Effect of unwrapped relative azimuth, SZA {sza:g}°, VZA {vza:g}°")
    ax.set_xticks(range(0, 361, 45))
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "crosscheck_psi_wrap.png", dpi=200)
    plt.close(fig)


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    cases = case_table()
    cases.to_csv(LOGS / "crosscheck_cases.csv", index=False)
    dry, wet = builtin_soils()
    pd.DataFrame({"wavelength": WAVELENGTHS, "dry": dry, "wet": wet}).to_csv(
        LOGS / "crosscheck_soil.csv", index=False)
    print(f"{len(cases)} cases written to {LOGS / 'crosscheck_cases.csv'}")

    diffs = [compare_python_backends(cases)]
    r_diffs = compare_r(cases)
    if r_diffs is not None:
        diffs.append(r_diffs)
    diffs = pd.concat(diffs, ignore_index=True)
    diffs.to_csv(LOGS / "crosscheck_differences.csv", index=False)
    summary = summarise(diffs)
    summary.to_csv(LOGS / "crosscheck_summary.csv", index=False)

    psi = psi_wrap_effect()
    psi.to_csv(LOGS / "crosscheck_psi_wrap.csv", index=False)
    anis = resv_vs_rsot()
    anis.to_csv(LOGS / "crosscheck_resv_vs_rsot.csv", index=False)

    plot_spectra(cases)
    plot_psi_bug()

    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", "{:.2e}".format)
    print("\nMaximum |difference| and mean RMSD by spectral region:")
    print(summary.to_string(index=False))
    print("\nUnwrapped psi (raa vs 360 - raa), relative error % in rsot:")
    print(psi.groupby("wavelength")["relative_error_pct"].agg(["min", "max"]).to_string())
    pd.set_option("display.float_format", "{:.3f}".format)
    print("\nHotspot / forward-scatter ratio, rsot vs resv (vza = sza, principal plane):")
    print(anis.pivot_table(index=["sza", "wavelength"], columns="factor",
                           values="hotspot_to_forward_ratio").to_string())


if __name__ == "__main__":
    main()
