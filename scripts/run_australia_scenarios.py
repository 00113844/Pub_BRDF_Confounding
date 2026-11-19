"""Australia geometry scenarios for the COMPAG paper (E1 geometry, E2 same canopy -> different VI).

Usage:
    python scripts/run_australia_scenarios.py            # E1 + E2
    python scripts/run_australia_scenarios.py e1         # one experiment

Writes results/logs/aus_*.csv|parquet and results/figures/aus_*.png. Geometry LUTs are cached in
results/lut/. Reflectance factor: rsot (BRF, direct sun) is the primary factor; resv (sun + sky)
is reported alongside it. Delta values are relative to the reference geometry
(geometry_scenarios.REFERENCE_GEOMETRY: nadir, SZA 45 deg) for the same canopy and factor.
"""

from __future__ import annotations

import sys
import time as _time
from datetime import date, time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from publication_spectral_data.crop_params import load_growth_stages, stage_params  # noqa: E402
from publication_spectral_data.geometry_scenarios import (  # noqa: E402
    REFERENCE_GEOMETRY,
    australia_grid,
    handheld_geometry,
    load_sites,
    monthly_dates,
    sentinel2_geometry,
    uav_geometry,
)
from publication_spectral_data.indices import INDICES  # noqa: E402
from publication_spectral_data.lut import cached_lut  # noqa: E402
from publication_spectral_data.prosail_engine import CanopyParams  # noqa: E402

LOGS = ROOT / "results" / "logs"
FIGS = ROOT / "results" / "figures"
FACTORS = ("rsot", "resv")
INDEX_NAMES = tuple(INDICES)
CLOCK_TIMES = [time(h, 0) for h in range(9, 16)]
MAP_MONTHS = (1, 4, 7, 10)
MONTH_NAMES = {1: "January", 4: "April", 7: "July", 10: "October"}
UAV_TIME = time(11, 0)

# Categorical slots (dataviz reference palette, fixed order) and map colour maps.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQ_CMAP = "Blues"
DIV_CMAP = "RdBu_r"
HIGHLIGHT_SITES = ["Darwin", "Gatton", "Geraldton", "Esperance", "Wagga Wagga", "Smithton"]


# --------------------------------------------------------------------------- canopies

# Z65 is excluded from the study canopies (author's decision, 2026-11-19): its LAI (1.7, rain-fed
# Horsham, planimeter green-leaf area) comes from a different source and measurement type than the
# other wheat stages (LAI-2200, irrigated, Beijing), so Z55-Z65-Z75 was not one crop's trajectory.
# The sourced row stays in data/crop_parameters/growth_stages.csv.
EXCLUDED_WHEAT_STAGES = {65}


def canopies() -> dict[str, CanopyParams]:
    """Ryegrass reference (data/ryegrass-params.yaml = CanopyParams defaults), two LAI levels of it,
    and every wheat Zadoks row that has a sourced typical LAI and Cab."""
    ref = CanopyParams()
    out = {"ryegrass_ref": ref,
           "ryegrass_lai1.0": ref.updated(lai=1.0),
           "ryegrass_lai4.0": ref.updated(lai=4.0)}
    table = load_growth_stages()
    for _, row in table[(table["crop"] == "wheat") & table["lai_typ"].notna() & table["cab"].notna()].iterrows():
        if int(row["zadoks"]) in EXCLUDED_WHEAT_STAGES:
            continue
        params, _ = stage_params(row, "lai_typ")  # blank inputs (e.g. hspot) fall back to defaults
        out[f"wheat_Z{int(row['zadoks'])}"] = params
    return out


# --------------------------------------------------------------------------- E1 geometry

def e1_geometry() -> dict[str, pd.DataFrame]:
    sites = load_sites()
    months = monthly_dates()
    geo = {
        "handheld": handheld_geometry(sites, months, CLOCK_TIMES),
        "s2": sentinel2_geometry(sites, months),
        "uav": uav_geometry(sites, months, UAV_TIME),
    }
    for name, df in geo.items():
        df.to_csv(LOGS / f"aus_geometry_{name}_sites.csv", index=False)

    grid = australia_grid(0.5)
    geo["s2_grid"] = sentinel2_geometry(grid, months)
    geo["s2_grid"].to_parquet(LOGS / "aus_geometry_s2_grid.parquet", index=False)

    _fig_sza_maps(geo["s2_grid"])
    _fig_handheld_sza(geo["handheld"])
    return geo


def _map_axes(n: int, title: str):
    import cartopy.crs as ccrs
    fig, axes = plt.subplots(1, n, figsize=(3.4 * n, 3.6), subplot_kw={"projection": ccrs.PlateCarree()},
                             constrained_layout=True)
    for ax in np.atleast_1d(axes):
        ax.set_extent([112.5, 154.0, -44.0, -10.0], crs=ccrs.PlateCarree())
        ax.coastlines("50m", linewidth=0.5, color="#52514e")
    fig.suptitle(title, fontsize=10)
    return fig, np.atleast_1d(axes)


def _scatter_map(ax, df, col, **kw):
    import cartopy.crs as ccrs
    return ax.scatter(df["lon"], df["lat"], c=df[col], s=4, marker="s", linewidths=0,
                      transform=ccrs.PlateCarree(), **kw)


# Site symbols by farming system (data/sites/australia_sites.csv, column "system"). Shape carries
# identity, so the key stays readable in greyscale and over the sequential SZA colour map.
SITE_SYSTEMS = {
    "dairy_pasture": {"label": "Dairy pasture district", "marker": "o", "face": "#ffffff"},
    "wheat": {"label": "Wheatbelt", "marker": "^", "face": "#eda100"},
    "tropical_control": {"label": "Tropical latitude control", "marker": "s", "face": "#8a8986"},
}
# Label offsets (points) for the site key map, chosen by hand so clustered sites do not overlap.
SITE_LABEL_OFFSETS = {
    "Darwin": (-6, 4, "right"), "Katherine": (6, 2, "left"), "Kununurra": (-8, -6, "right"),
    "Atherton": (6, 0, "left"), "Gatton": (-8, 0, "right"), "Moree": (6, 0, "left"),
    "Geraldton": (-6, 0, "right"), "Northam": (-6, 4, "right"), "Merredin": (6, 4, "left"),
    "Esperance": (6, -4, "left"), "Busselton": (-8, -2, "right"), "Albany": (2, -10, "left"),
    "Roseworthy": (-8, 7, "right"), "Mount Gambier": (-6, -4, "right"), "Horsham": (2, 7, "left"),
    "Hamilton": (6, 2, "left"), "Warrnambool": (6, -7, "left"), "Wagga Wagga": (6, 0, "left"),
    "Smithton": (9, -2, "left"),
}
FIG_METADATA = {"Author": "Gustavo Togeiro de Alckmin"}


def _plot_sites(ax, sites: pd.DataFrame, size: float = 22, labels: bool = False) -> None:
    import cartopy.crs as ccrs
    for system, style in SITE_SYSTEMS.items():
        sub = sites[sites["system"] == system]
        ax.scatter(sub["lon"], sub["lat"], marker=style["marker"], s=size, c=style["face"],
                   edgecolors="#1f1f1d", linewidths=0.8, transform=ccrs.PlateCarree(), zorder=5,
                   label=f"{style['label']} (n = {len(sub)})")
        if labels:
            for r in sub.itertuples(index=False):
                dx, dy, ha = SITE_LABEL_OFFSETS.get(r.site, (6, 0, "left"))
                ax.annotate(r.site, (r.lon, r.lat), xytext=(dx, dy), textcoords="offset points",
                            ha=ha, va="center", fontsize=6.5, color="#1f1f1d", zorder=6,
                            xycoords=ccrs.PlateCarree()._as_mpl_transform(ax))


def _fig_sza_maps(grid_geo: pd.DataFrame) -> None:
    """Figure 1: site key map (19 named sites by farming system) + SZA at the S2 overpass."""
    import cartopy.crs as ccrs
    nadir = grid_geo[grid_geo["across_track_km"] == 0]
    sites = load_sites()
    fig = plt.figure(figsize=(11.5, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1.35, 1, 1])
    extent = [112.5, 154.0, -44.0, -10.0]
    key = fig.add_subplot(gs[:, 0], projection=ccrs.PlateCarree())
    key.set_extent(extent, crs=ccrs.PlateCarree())
    key.coastlines("50m", linewidth=0.6, color="#52514e")
    _plot_sites(key, sites, size=40, labels=True)
    key.set_title("(a) Named sites (town-centre coordinates)", fontsize=9)
    key.legend(loc="lower left", fontsize=6.5, frameon=True, framealpha=0.9, edgecolor="#cfcdc8")

    vmin, vmax = nadir["sza"].min(), nadir["sza"].max()
    axes = []
    for i, m in enumerate(MAP_MONTHS):
        ax = fig.add_subplot(gs[i // 2, 1 + i % 2], projection=ccrs.PlateCarree())
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.coastlines("50m", linewidth=0.5, color="#52514e")
        sub = nadir[pd.to_datetime(nadir["time_local"].astype(str).str[:10]).dt.month == m]
        sc = _scatter_map(ax, sub, "sza", cmap=SEQ_CMAP, vmin=vmin, vmax=vmax)
        _plot_sites(ax, sites, size=14)
        ax.set_title(f"({'bcde'[i]}) {MONTH_NAMES[m]}", fontsize=9)
        axes.append(ax)
    fig.colorbar(sc, ax=axes, shrink=0.8, label="Solar zenith angle at the Sentinel-2 overpass (°)")
    fig.savefig(FIGS / "aus_sza_maps_s2.png", dpi=300, metadata=FIG_METADATA)
    fig.savefig(FIGS / "aus_sza_maps_s2.pdf", metadata={**FIG_METADATA, "Creator": FIG_METADATA["Author"]})
    plt.close(fig)


def _fig_handheld_sza(hh: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True, constrained_layout=True)
    for ax, m in zip(axes, (1, 7)):
        sub = hh[hh["time_local"].map(lambda t: t.month) == m]
        for color, site in zip(SERIES, HIGHLIGHT_SITES):
            s = sub[sub["site"] == site]
            ax.plot(s["clock_time"], s["sza"], color=color, lw=2, marker="o", ms=4, label=site)
        ax.set_title(f"15 {MONTH_NAMES[m]} (local clock time)", fontsize=9)
        ax.set_xlabel("Clock time")
        ax.grid(alpha=0.3, lw=0.5)
    axes[0].set_ylabel("Solar zenith angle (°)")
    axes[0].invert_yaxis()
    axes[1].legend(fontsize=7, frameon=False)
    fig.suptitle("Handheld protocol '09:00-15:00': solar zenith by site", fontsize=10)
    fig.savefig(FIGS / "aus_handheld_sza.png", dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------- E2 VI

def vi_table(geo: pd.DataFrame, lut, canopy: str) -> pd.DataFrame:
    """All indices x factors at each geometry row, with delta to the reference geometry."""
    ref = REFERENCE_GEOMETRY
    out = []
    for factor in FACTORS:
        part = geo.copy()
        part["canopy"], part["factor"] = canopy, factor
        for name in INDEX_NAMES:
            values = lut.index_at(name, geo["sza"].to_numpy(), geo["vza"].to_numpy(),
                                  geo["raa"].to_numpy(), factor)
            ref_value = float(lut.index_at(name, ref["sza"], ref["vza"], ref["raa"], factor))
            part[name] = values
            part[f"d{name}"] = values - ref_value
            part[f"rel{name}_pct"] = 100 * (values - ref_value) / ref_value
        out.append(part)
    return pd.concat(out, ignore_index=True)


def e2_vi(geo: dict[str, pd.DataFrame]) -> None:
    tables = {"handheld": [], "s2": [], "uav": []}
    luts = {}
    for name, params in canopies().items():
        t0 = _time.time()
        luts[name] = cached_lut(params)
        print(f"  LUT {name}: {_time.time() - t0:.1f} s")
        for sensor in tables:
            tables[sensor].append(vi_table(geo[sensor], luts[name], name))
    for sensor, parts in tables.items():
        pd.concat(parts, ignore_index=True).to_csv(LOGS / f"aus_vi_{sensor}_sites.csv", index=False)

    grid = vi_table(geo["s2_grid"], luts["ryegrass_ref"], "ryegrass_ref")
    grid.to_parquet(LOGS / "aus_vi_s2_grid_ryegrass.parquet", index=False)

    _fig_dvi_maps(grid)
    hh = pd.concat(tables["handheld"], ignore_index=True)
    _fig_handheld_dvi(hh)
    _fig_site_month(pd.concat(tables["s2"], ignore_index=True))
    _summary(hh, pd.concat(tables["s2"], ignore_index=True), pd.concat(tables["uav"], ignore_index=True), grid)


def _month(df):
    return df["time_local"].map(lambda t: pd.Timestamp(t).month)


def _fig_dvi_maps(grid: pd.DataFrame) -> None:
    sub_all = grid[(grid["factor"] == "rsot") & (grid["across_track_km"] == 0)].copy()
    sub_all["month"] = _month(sub_all)
    for idx in ("NDVI", "NDRE"):
        col = f"rel{idx}_pct"
        lim = np.nanmax(np.abs(sub_all[col]))
        fig, axes = _map_axes(len(MAP_MONTHS),
                              f"Ryegrass reference canopy (LAI 2.5): {idx} at the Sentinel-2 overpass, nadir, "
                              f"relative to nadir/SZA 45° (BRF)")
        for ax, m in zip(axes, MAP_MONTHS):
            sc = _scatter_map(ax, sub_all[sub_all["month"] == m], col, cmap=DIV_CMAP,
                              norm=TwoSlopeNorm(0, -lim, lim))
            ax.set_title(MONTH_NAMES[m], fontsize=9)
        fig.colorbar(sc, ax=axes, shrink=0.8, label=f"Δ{idx} (%)")
        fig.savefig(FIGS / f"aus_d{idx.lower()}_maps_s2.png", dpi=200)
        plt.close(fig)


def _fig_handheld_dvi(hh: pd.DataFrame) -> None:
    sub = hh[(hh["factor"] == "rsot") & (hh["canopy"] == "ryegrass_ref")].copy()
    sub["month"] = _month(sub)
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True, constrained_layout=True)
    for ax, m in zip(axes, (1, 7)):
        s_m = sub[sub["month"] == m]
        for color, site in zip(SERIES, HIGHLIGHT_SITES):
            s = s_m[s_m["site"] == site]
            ax.plot(s["clock_time"], s["relNDVI_pct"], color=color, lw=2, marker="o", ms=4, label=site)
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_title(f"15 {MONTH_NAMES[m]}", fontsize=9)
        ax.set_xlabel("Clock time")
        ax.grid(alpha=0.3, lw=0.5)
    axes[0].set_ylabel("ΔNDVI vs nadir/SZA 45° (%)")
    axes[1].legend(fontsize=7, frameon=False)
    fig.suptitle("Same ryegrass canopy (LAI 2.5), nadir handheld, BRF: NDVI by site and clock time",
                 fontsize=10)
    fig.savefig(FIGS / "aus_handheld_dndvi.png", dpi=200)
    plt.close(fig)


def _fig_site_month(s2: pd.DataFrame) -> None:
    sub = s2[(s2["factor"] == "rsot") & (s2["canopy"] == "ryegrass_ref") & (s2["across_track_km"] == 0)].copy()
    sub["month"] = _month(sub)
    order = load_sites().sort_values("lat", ascending=False)["site"].tolist()
    for idx in ("NDVI", "NDRE"):
        piv = sub.pivot_table(index="site", columns="month", values=f"rel{idx}_pct").reindex(order)
        lim = np.nanmax(np.abs(piv.to_numpy()))
        fig, ax = plt.subplots(figsize=(7, 5.5), constrained_layout=True)
        im = ax.imshow(piv.to_numpy(), cmap=DIV_CMAP, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
        ax.set_xticks(range(12), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
        ax.set_yticks(range(len(piv)), piv.index)
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.iat[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6,
                            color="white" if abs(v) > 0.6 * lim else "#0b0b0b")
        fig.colorbar(im, ax=ax, label=f"Δ{idx} (%)")
        ax.set_title(f"Ryegrass reference: {idx} at the Sentinel-2 overpass (nadir, BRF), sites north to south",
                     fontsize=9)
        fig.savefig(FIGS / f"aus_site_month_d{idx.lower()}_s2.png", dpi=200)
        plt.close(fig)


def _summary(hh, s2, uav, grid) -> None:
    rows = []
    for sensor, df in (("handheld_sites", hh), ("s2_sites", s2), ("uav_sites", uav), ("s2_grid", grid)):
        for (canopy, factor), g in df.groupby(["canopy", "factor"]):
            row = {"sensor": sensor, "canopy": canopy, "factor": factor, "n": len(g)}
            for idx in INDEX_NAMES:
                v = g[idx]
                row[f"{idx}_range"] = v.max() - v.min()
                row[f"{idx}_rel_p05_pct"] = g[f"rel{idx}_pct"].quantile(0.05)
                row[f"{idx}_rel_p95_pct"] = g[f"rel{idx}_pct"].quantile(0.95)
            rows.append(row)
    pd.DataFrame(rows).to_csv(LOGS / "aus_vi_summary.csv", index=False)


# --------------------------------------------------------------------------- E3 + E4 trait error

TRAIT_INDICES = ("NDVI", "NDRE", "GNDVI", "MTCI")
SENSOR_LABELS = {"handheld": "Handheld 09-15 h", "s2": "Sentinel-2", "uav": "UAV 11 h"}


def e3_e4_traits() -> None:
    from publication_spectral_data.traits import equivalent_trait, fit_all, model_table, trait_values, training_set

    print("  training set ...")
    train = training_set(3000, indices=TRAIT_INDICES, seed=0)
    models = fit_all(train, TRAIT_INDICES)
    model_table(models).to_csv(LOGS / "aus_trait_models.csv", index=False)

    cans = canopies()
    out = []
    for sensor in ("handheld", "s2", "uav"):
        vi = pd.read_csv(LOGS / f"aus_vi_{sensor}_sites.csv")
        vi = vi[vi["factor"] == "rsot"]
        for canopy, g in vi.groupby("canopy"):
            params = cans[canopy]
            truth = trait_values(params)
            part = g[["site", "state", "lat", "lon", "time_local", "sza", "vza", "raa", "canopy"]].copy()
            part["sensor"] = sensor
            ref_row = vi_table(pd.DataFrame([{**REFERENCE_GEOMETRY}]), cached_lut(params), canopy)
            ref_row = ref_row[ref_row["factor"] == "rsot"].iloc[0]
            for idx in ("NDVI", "NDRE"):
                for trait in ("lai", "ccc"):
                    eq = equivalent_trait(g[idx].to_numpy(), idx, params, REFERENCE_GEOMETRY, trait=trait)
                    part[f"eq_{trait}_{idx}_err_pct"] = 100 * (eq - truth[trait]) / truth[trait]
            for idx in TRAIT_INDICES:
                for trait in ("lai", "biomass", "ccc"):
                    m = models[(idx, trait)]
                    pred = m.predict(g[idx].to_numpy())
                    pred_ref = float(m.predict(ref_row[idx]))
                    part[f"emp_{trait}_{idx}_err_pct"] = 100 * (pred - truth[trait]) / truth[trait]
                    part[f"emp_{trait}_{idx}_geom_pct"] = 100 * (pred - pred_ref) / pred_ref
            out.append(part)
    errors = pd.concat(out, ignore_index=True)
    errors.to_csv(LOGS / "aus_trait_errors_sites.csv", index=False)

    grid = pd.read_parquet(LOGS / "aus_vi_s2_grid_ryegrass.parquet")
    grid = grid[(grid["factor"] == "rsot") & (grid["across_track_km"] == 0)].copy()
    params = cans["ryegrass_ref"]
    grid["eq_lai_NDVI_err_pct"] = 100 * (equivalent_trait(grid["NDVI"].to_numpy(), "NDVI", params,
                                                          REFERENCE_GEOMETRY) - params.lai) / params.lai
    grid[["site", "lat", "lon", "time_local", "sza", "NDVI", "eq_lai_NDVI_err_pct"]].to_parquet(
        LOGS / "aus_trait_errors_s2_grid_ryegrass.parquet", index=False)

    _fig_eq_lai_map(grid)
    _fig_trait_error_boxes(errors)
    rows = []
    for (sensor, canopy), g in errors.groupby(["sensor", "canopy"]):
        row = {"sensor": sensor, "canopy": canopy, "n": len(g)}
        for col in [c for c in errors.columns if c.endswith("_pct")]:
            row[f"{col}_p05"] = g[col].quantile(0.05)
            row[f"{col}_p95"] = g[col].quantile(0.95)
        rows.append(row)
    pd.DataFrame(rows).to_csv(LOGS / "aus_trait_errors_summary.csv", index=False)


def _fig_eq_lai_map(grid: pd.DataFrame) -> None:
    grid = grid.copy()
    grid["month"] = _month(grid)
    lim = np.nanmax(np.abs(grid["eq_lai_NDVI_err_pct"]))
    fig, axes = _map_axes(len(MAP_MONTHS), "Ryegrass reference (true LAI 2.5): LAI read from NDVI at the "
                                           "Sentinel-2 overpass with a model calibrated at nadir/SZA 45°")
    for ax, m in zip(axes, MAP_MONTHS):
        sc = _scatter_map(ax, grid[grid["month"] == m], "eq_lai_NDVI_err_pct", cmap=DIV_CMAP,
                          norm=TwoSlopeNorm(0, -lim, lim))
        ax.set_title(MONTH_NAMES[m], fontsize=9)
    fig.colorbar(sc, ax=axes, shrink=0.8, label="LAI error (%)")
    fig.savefig(FIGS / "aus_lai_error_maps_s2.png", dpi=200)
    plt.close(fig)


def _fig_trait_error_boxes(errors: pd.DataFrame) -> None:
    order = list(canopies())
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.5), sharex=True, constrained_layout=True)
    for ax, (col, label) in zip(axes, (("eq_lai_NDVI_err_pct", "LAI error from NDVI (%)"),
                                       ("eq_ccc_NDRE_err_pct", "CCC (N/CP proxy) error from NDRE (%)"))):
        for k, (sensor, color) in enumerate(zip(SENSOR_LABELS, SERIES)):
            data = [errors[(errors["sensor"] == sensor) & (errors["canopy"] == c)][col].dropna() for c in order]
            pos = np.arange(len(order)) + (k - 1) * 0.27
            bp = ax.boxplot(data, positions=pos, widths=0.22, whis=(5, 95), showfliers=False,
                            patch_artist=True, medianprops={"color": "#0b0b0b", "lw": 1})
            for patch in bp["boxes"]:
                patch.set_facecolor(color)
                patch.set_edgecolor(color)
            ax.plot([], [], color=color, lw=6, label=SENSOR_LABELS[sensor])
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.3, lw=0.5)
    axes[0].legend(fontsize=7, frameon=False, ncol=3)
    axes[1].set_xticks(range(len(order)), order, rotation=30, ha="right", fontsize=8)
    fig.suptitle("Trait error from geometry alone (perfect canopy-specific model; whiskers 5-95 %)",
                 fontsize=10)
    fig.savefig(FIGS / "aus_trait_error_boxes.png", dpi=200, metadata=FIG_METADATA)
    plt.close(fig)


# --------------------------------------------------------------------------- E5 multi-angle

E5_CANOPIES = ("ryegrass_ref", "ryegrass_lai1.0", "wheat_Z30", "wheat_Z55")
# Views as (vza, raa): raa = 0 looks with the sun behind the sensor (hotspot side), 180 forward.
E5_VIEWS = [(0, 0), (20, 0), (20, 180), (35, 0), (35, 180), (20, 90), (35, 90), (10, 45), (10, 135)]
E5_SETS = {1: [0], 3: [0, 1, 2], 5: [0, 1, 2, 3, 4], 9: list(range(9))}
E5_NOISE = 0.02
E5_REPEATS = 5
E5_CANDIDATES = 2000
E5_METHODS = ["Empirical NDVI model", "Kernel normalisation + NDVI model", "LUT inversion",
              "LUT + least-squares inversion"]


def _e5_case(task: dict) -> list[dict]:
    """All canopies, noise repeats and view sets for one sun position (one site and month)."""
    from publication_spectral_data.indices import INDEX_BANDS, compute_index
    from publication_spectral_data.multiangle import (S2_BANDS, add_noise, invert, invert_lsq,
                                                      normalise_to_reference, simulate_candidates)
    from publication_spectral_data.prosail_engine import simulate
    from publication_spectral_data.traits import TRAINING_RANGES, trait_values

    rng = np.random.default_rng(task["seed"])
    geoms = [(task["sza"], v, r) for v, r in E5_VIEWS]
    candidates, model, cans = task["candidates"], task["model"], task["canopies"]
    cand_refl, cand_traits = simulate_candidates(candidates, geoms, bands=S2_BANDS)
    rows = []
    for canopy in E5_CANOPIES:
        params = cans[canopy]
        truth = trait_values(params)
        spectra = [simulate(params, *g)["rsot"] for g in geoms]
        idx_bands = np.array([[s[w - 400] for w in INDEX_BANDS] for s in spectra])
        s2_bands = np.array([[s[w - 400] for w in S2_BANDS] for s in spectra])
        for rep in range(E5_REPEATS):
            obs_idx = add_noise(idx_bands, E5_NOISE, rng)
            obs_s2 = add_noise(s2_bands, E5_NOISE, rng)
            base = {"site": task["site"], "month": task["month"], "sza": task["sza"],
                    "canopy": canopy, "rep": rep}

            def add(method, K, est, extra=None):
                for trait in ("lai", "ccc"):
                    rows.append({**base, "method": method, "K": K, "trait": trait,
                                 "estimate": est[trait],
                                 "err_pct": 100 * (est[trait] - truth[trait]) / truth[trait],
                                 **(extra or {})})

            ndvi_nadir = compute_index("NDVI", dict(zip(INDEX_BANDS, obs_idx[0])))
            add(E5_METHODS[0], 1, {t: float(model[("NDVI", t)].predict(ndvi_nadir)) for t in ("lai", "ccc")})
            for K, views in E5_SETS.items():
                if K >= 3:
                    sel = [geoms[i] for i in views]
                    norm = normalise_to_reference(obs_idx[views], *zip(*sel), REFERENCE_GEOMETRY)
                    ndvi_ref = compute_index("NDVI", dict(zip(INDEX_BANDS, norm)))
                    add(E5_METHODS[1], K, {t: float(model[("NDVI", t)].predict(ndvi_ref)) for t in ("lai", "ccc")})
                add(E5_METHODS[2], K, invert(obs_s2, cand_refl, cand_traits, views=views, n_best=20))
                est = invert_lsq(obs_s2, geoms, cand_refl, candidates, TRAINING_RANGES, views=views,
                                 noise_sd=E5_NOISE, n_starts=2)
                add(E5_METHODS[3], K, est, {"chi2_red": est["chi2_red"], "at_bound": est["at_bound"],
                                            "lidfa_est": est["lidfa"], "hspot_est": est["hspot"]})
    return rows


def e5_multiangle(processes: int | None = None) -> None:
    import os
    from multiprocessing import Pool

    from publication_spectral_data.traits import TRAINING_RANGES, fit_all, latin_hypercube, training_set

    sites = load_sites()
    sites = sites[sites["site"].isin(HIGHLIGHT_SITES)]
    sun = handheld_geometry(sites, [date(2026, m, 15) for m in MAP_MONTHS], [UAV_TIME])
    model = fit_all(training_set(3000, indices=("NDVI",), seed=0), ["NDVI"], ["lai", "ccc"])
    candidates = latin_hypercube(E5_CANDIDATES, TRAINING_RANGES, seed=7)
    cans = canopies()
    tasks = [{"site": c.site, "month": pd.Timestamp(c.time_local).month, "sza": float(c.sza),
              "seed": 1000 + i, "candidates": candidates, "model": model, "canopies": cans}
             for i, c in enumerate(sun.itertuples(index=False))]
    processes = processes or max(1, min(len(tasks), (os.cpu_count() or 2) - 1))
    print(f"  {len(tasks)} sun positions on {processes} processes ...")
    with Pool(processes) as pool:
        rows = [r for part in pool.imap_unordered(_e5_case, tasks) for r in part]
    res = pd.DataFrame(rows).sort_values(["site", "month", "canopy", "rep", "method", "K", "trait"])
    res.to_csv(LOGS / "aus_multiangle_cases.csv", index=False)

    site_month = res.groupby(["method", "K", "trait", "canopy", "site", "month"])["err_pct"].mean()
    spread = (site_month.groupby(["method", "K", "trait", "canopy"])
              .agg(lambda x: x.quantile(0.95) - x.quantile(0.05)).rename("location_spread_pct"))
    summary = (res.assign(abs_err=res["err_pct"].abs())
               .groupby(["method", "K", "trait", "canopy"])
               .agg(mean_err_pct=("err_pct", "mean"), mae_pct=("abs_err", "mean"),
                    p95_abs_pct=("abs_err", lambda x: x.quantile(0.95)), n=("err_pct", "size"))
               .join(spread).reset_index())
    summary.to_csv(LOGS / "aus_multiangle_summary.csv", index=False)
    _fig_multiangle(summary)


def _fig_multiangle(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(9.5, 6.5), sharex=True, constrained_layout=True)
    metrics = (("mae_pct", "Mean absolute error (%)"),
               ("location_spread_pct", "Spread across sites x months (%)\n(5th-95th pct of site-month mean error)"))
    for col, (trait, label) in enumerate((("lai", "LAI"), ("ccc", "CCC (N/CP proxy)"))):
        for row, (metric, ylabel) in enumerate(metrics):
            ax = axes[row, col]
            sub = summary[summary["trait"] == trait]
            for color, method in zip(SERIES, E5_METHODS):
                s = sub[sub["method"] == method].groupby("K")[metric].mean()
                ax.plot(s.index, s.values, color=color, lw=2, marker="o", ms=6, label=method)
            ax.set_xticks(list(E5_SETS))
            ax.set_ylim(bottom=0)
            ax.grid(alpha=0.3, lw=0.5)
            if col == 0:
                ax.set_ylabel(ylabel, fontsize=8)
            if row == 0:
                ax.set_title(label, fontsize=9)
            else:
                ax.set_xlabel("Number of view angles (K)")
    axes[0, 0].legend(fontsize=7, frameon=False)
    fig.suptitle(f"Multi-angle retrieval, UAV at 11:00, 6 sites x 4 months x 4 canopies, "
                 f"{E5_NOISE:.0%} radiometric noise (mean over canopies)", fontsize=10)
    fig.savefig(FIGS / "aus_multiangle_error.png", dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------- main

def main(argv: list[str]) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    wanted = set(a.lower() for a in argv) or {"e1", "e2", "e3", "e5"}
    t0 = _time.time()
    if wanted & {"e1", "e2"}:
        print("E1 geometry ...")
        geo = e1_geometry()
        if "e2" in wanted:
            print("E2 vegetation indices ...")
            e2_vi(geo)
    if wanted & {"e3", "e4"}:
        print("E3/E4 trait errors ...")
        e3_e4_traits()
    if "e5" in wanted:
        print("E5 multi-angle ...")
        e5_multiangle()
    print(f"done in {_time.time() - t0:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
