"""PROSAIL BRDF Explorer (Streamlit).

Run from the repository root:  uv run streamlit run app/streamlit_app.py

Tabs:
  1. Simulator          -- spectrum at one geometry + polar BRDF of a vegetation index
  2. Location & time    -- click a map, pick date/time -> solar zenith/azimuth (pvlib)
  3. Growth stages      -- literature parameters per Zadoks stage, loaded into the simulator
"""

from __future__ import annotations

from datetime import date, datetime, time

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from publication_spectral_data.crop_params import DATA_FILE, LAI_LEVELS, load_growth_stages, stage_params
from publication_spectral_data.indices import INDEX_FORMULAS, INDICES, compute_index
from publication_spectral_data.prosail_engine import (
    FACTOR_LABELS,
    FACTORS,
    MAX_ZENITH,
    WAVELENGTHS,
    CanopyParams,
    brdf_grid,
    simulate,
)
from publication_spectral_data.solar import daily_course, local_timezone, solar_position

st.set_page_config(page_title="PROSAIL BRDF Explorer", layout="wide")

DEFAULTS = CanopyParams()
VZA_MAX = 80.0
COMPASS = "Compass (North up)"
RELATIVE = "Relative (sun's azimuth up)"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_initial_state = {
    **{f"p_{k}": v for k, v in DEFAULTS.to_dict().items()},
    "p_lidf1_a": -0.35, "p_lidf1_b": -0.15,          # Verhoef "spherical" for typelidf 1
    "p_typelidf_label": "Ellipsoidal (mean leaf angle)",
    "factor": "resv", "index": "NDVI",
    "sza": 30.0, "saa": 0.0, "vza": 0.0, "raa": 0.0,
    "orientation": RELATIVE, "grid_step": 10,
    "lat": -31.98, "lon": 115.82,                    # Perth, Western Australia
    "obs_date": date.today(), "obs_time": time(12, 0),
}
for key, value in _initial_state.items():
    st.session_state.setdefault(key, value)

LIDF_TYPES = {"Ellipsoidal (mean leaf angle)": 2, "Verhoef two-parameter": 1}


def current_params() -> CanopyParams:
    s = st.session_state
    typelidf = LIDF_TYPES[s["p_typelidf_label"]]
    lidfa, lidfb = (s["p_lidfa"], 0.0) if typelidf == 2 else (s["p_lidf1_a"], s["p_lidf1_b"])
    return CanopyParams(N=s["p_N"], cab=s["p_cab"], car=s["p_car"], cbrown=s["p_cbrown"],
                        cw=s["p_cw"], cm=s["p_cm"], lai=s["p_lai"], typelidf=typelidf,
                        lidfa=lidfa, lidfb=lidfb, hspot=s["p_hspot"], psoil=s["p_psoil"],
                        soil_scale=s["p_soil_scale"])


# Slider ranges; values loaded from the database are clipped into them
RANGES = {
    "N": (1.0, 3.0, 0.05), "cab": (0.0, 100.0, 0.5), "car": (0.0, 30.0, 0.5),
    "cbrown": (0.0, 1.0, 0.01), "cw": (0.001, 0.06, 0.001), "cm": (0.001, 0.03, 0.0005),
    "lai": (0.0, 10.0, 0.1), "lidfa": (0.0, 90.0, 1.0), "hspot": (0.0, 1.0, 0.005),
    "psoil": (0.0, 1.0, 0.05), "soil_scale": (0.0, 2.0, 0.05),
}


def apply_params(params: CanopyParams) -> None:
    """Callback: push parameters into the sidebar widgets."""
    for name, value in params.to_dict().items():
        if name == "typelidf":
            st.session_state["p_typelidf_label"] = next(k for k, v in LIDF_TYPES.items() if v == value)
        elif name in ("lidfa", "lidfb") and params.typelidf == 1:
            st.session_state[f"p_lidf1_{name[-1]}"] = float(np.clip(value, -1, 1))
        elif name in RANGES:
            lo, hi, _ = RANGES[name]
            st.session_state[f"p_{name}"] = float(np.clip(value, lo, hi))


def apply_sun(sza: float, saa: float) -> None:
    """Callback: use a computed sun position in the simulator."""
    st.session_state["sza"] = float(round(min(sza, MAX_ZENITH), 2))
    st.session_state["saa"] = float(round(saa, 2))
    st.session_state["orientation"] = COMPASS


# ---------------------------------------------------------------------------
# Cached model runs
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=64)
def cached_spectrum(params: CanopyParams, sza: float, vza: float, raa: float) -> dict:
    return simulate(params, sza, vza, raa)


@st.cache_data(show_spinner=False, max_entries=32)
def cached_grid(params: CanopyParams, sza: float, step: int, factor: str, index: str) -> pd.DataFrame:
    vza = np.arange(0, VZA_MAX + 0.1, step)
    raa = np.arange(0, 360, step)
    return brdf_grid(params, sza, vza, raa, factor=factor, index=index)


@st.cache_data(show_spinner=False, max_entries=16)
def cached_daily_index(params: CanopyParams, lat: float, lon: float, day: date,
                       factor: str, index: str) -> pd.DataFrame:
    course = daily_course(lat, lon, day, step_minutes=15)
    day_rows = course[course["sza"] <= MAX_ZENITH].copy()
    day_rows["value"] = [compute_index(index, simulate(params, sza, 0.0, 0.0)[factor])
                         for sza in day_rows["sza"]]
    return course.merge(day_rows[["time_local", "value"]], on="time_local", how="left")


@st.cache_data(show_spinner=False)
def cached_noon_sza(lat: float, lon: float, year: int) -> pd.DataFrame:
    rows = []
    for day in pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="7D"):
        course = daily_course(lat, lon, day.date(), step_minutes=10)
        rows.append({"date": day, "min_sza": course["sza"].min()})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def cached_stages() -> pd.DataFrame | None:
    return load_growth_stages() if DATA_FILE.exists() else None


# ---------------------------------------------------------------------------
# Sidebar: PROSAIL inputs
# ---------------------------------------------------------------------------
def slider(name: str, label: str, fmt: str = "%.3g", help: str | None = None) -> None:
    lo, hi, step = RANGES[name]
    st.slider(label, lo, hi, step=step, key=f"p_{name}", format=fmt, help=help)


with st.sidebar:
    st.header("PROSAIL inputs")
    with st.expander("Leaf (PROSPECT-5B)", expanded=True):
        slider("N", "Leaf structure N", "%.2f")
        slider("cab", "Chlorophyll a+b (µg/cm²)", "%.1f")
        slider("car", "Carotenoids (µg/cm²)", "%.1f")
        slider("cbrown", "Brown pigment (a.u.)", "%.2f")
        slider("cw", "Equivalent water thickness (cm)", "%.3f")
        slider("cm", "Dry matter (g/cm²)", "%.4f")
    with st.expander("Canopy (4SAIL)", expanded=True):
        slider("lai", "Leaf area index (m²/m²)", "%.1f")
        st.radio("Leaf angle distribution", list(LIDF_TYPES), key="p_typelidf_label")
        if LIDF_TYPES[st.session_state["p_typelidf_label"]] == 2:
            slider("lidfa", "Mean leaf angle (°)", "%.0f",
                   help="0° = horizontal leaves (planophile), 90° = vertical (erectophile)")
        else:
            st.slider("LIDF a (mean slope)", -1.0, 1.0, step=0.05, key="p_lidf1_a")
            st.slider("LIDF b (bimodality)", -1.0, 1.0, step=0.05, key="p_lidf1_b")
            if abs(st.session_state["p_lidf1_a"]) + abs(st.session_state["p_lidf1_b"]) > 1:
                st.error("|a| + |b| must not exceed 1")
        slider("hspot", "Hotspot parameter", "%.3f", help="Leaf size / canopy height")
    with st.expander("Soil", expanded=False):
        slider("psoil", "Soil moisture mix (0 = wet, 1 = dry)", "%.2f")
        slider("soil_scale", "Soil brightness multiplier", "%.2f")
    st.header("Output")
    st.selectbox("Reflectance factor", FACTORS, key="factor", format_func=lambda f: f"{f}: {FACTOR_LABELS[f]}")
    st.selectbox("Vegetation index", list(INDICES), key="index",
                 help="; ".join(f"{k} = {v}" for k, v in INDEX_FORMULAS.items()))

params = current_params()

st.title("PROSAIL BRDF Explorer")
st.caption("PROSPECT-5B + 4SAIL (patched PyProSAIL Fortran). Angles in degrees; "
           "relative azimuth 0° is the hotspot (sensor on the sun's side).")

if params.typelidf == 1 and abs(params.lidfa) + abs(params.lidfb) > 1:
    st.error("Fix the leaf angle distribution in the sidebar: |a| + |b| must not exceed 1.")
    st.stop()

tab_sim, tab_loc, tab_stage = st.tabs(["Simulator", "Location & time", "Growth stages"])

# ---------------------------------------------------------------------------
# Tab 1: Simulator
# ---------------------------------------------------------------------------
with tab_sim:
    factor, index = st.session_state["factor"], st.session_state["index"]

    geo = st.columns(4)
    geo[0].number_input("Solar zenith (°)", 0.0, MAX_ZENITH, step=1.0, key="sza")
    geo[1].number_input("Solar azimuth (°, from North)", 0.0, 360.0, step=1.0, key="saa",
                        help="Only used to orient the polar plot to the compass")
    geo[2].number_input("View zenith (°)", 0.0, VZA_MAX, step=1.0, key="vza")
    geo[3].number_input("Relative azimuth (°)", 0.0, 360.0, step=5.0, key="raa",
                        help="0° = hotspot side, 180° = forward scatter")
    sza, saa = st.session_state["sza"], st.session_state["saa"]

    col_spec, col_brdf = st.columns([1, 1])

    with col_spec:
        st.subheader("Spectrum")
        spec = cached_spectrum(params, sza, st.session_state["vza"], st.session_state["raa"])
        show_all = st.checkbox("Show all reflectance factors", value=False)
        shown = FACTORS if show_all else (factor,)
        spec_df = pd.DataFrame({"wavelength": WAVELENGTHS, **{f: spec[f] for f in shown}})
        fig = px.line(spec_df.melt("wavelength", var_name="factor", value_name="reflectance"),
                      x="wavelength", y="reflectance", color="factor",
                      labels={"wavelength": "Wavelength (nm)", "reflectance": "Reflectance factor"})
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
        st.plotly_chart(fig, width="stretch")
        st.metric(f"{index} ({factor})", f"{compute_index(index, spec[factor]):.3f}")
        st.download_button("Download spectrum (CSV)",
                           pd.DataFrame({"wavelength": WAVELENGTHS, **{f: spec[f] for f in FACTORS}})
                           .to_csv(index=False), "prosail_spectrum.csv", "text/csv")

    with col_brdf:
        st.subheader(f"{index} BRDF")
        ctrl = st.columns(2)
        ctrl[0].selectbox("Angle step (°)", [5, 10, 15], key="grid_step")
        ctrl[1].radio("Orientation", [RELATIVE, COMPASS], key="orientation")
        with st.spinner("Running PROSAIL over the view hemisphere..."):
            grid = cached_grid(params, sza, st.session_state["grid_step"], factor, index)
        step = st.session_state["grid_step"]
        compass = st.session_state["orientation"] == COMPASS
        # raa is measured from the sun's azimuth, so the sensor's compass azimuth is saa + raa
        theta = (grid["raa"] + saa) % 360 if compass else grid["raa"]
        fig = go.Figure(go.Barpolar(
            r=np.full(len(grid), step, dtype=float),
            base=np.clip(grid["vza"] - step / 2, 0, None),
            theta=theta, width=step,
            marker=dict(color=grid["value"], colorscale="YlGn", showscale=True,
                        colorbar=dict(title=index), line=dict(width=0)),
            customdata=np.column_stack([grid["vza"], grid["raa"], grid["value"]]),
            hovertemplate="VZA %{customdata[0]:.0f}°<br>RAA %{customdata[1]:.0f}°"
                          "<br>" + index + " %{customdata[2]:.3f}<extra></extra>",
        ))
        fig.add_trace(go.Scatterpolar(r=[sza], theta=[saa if compass else 0], mode="markers",
                                      marker=dict(symbol="star", size=16, color="gold",
                                                  line=dict(color="black", width=1)),
                                      name="Hotspot (VZA = SZA)", hoverinfo="name"))
        fig.update_layout(
            height=470, margin=dict(l=30, r=30, t=30, b=30), showlegend=False,
            polar=dict(radialaxis=dict(range=[0, VZA_MAX + step / 2], ticksuffix="°"),
                       angularaxis=dict(rotation=90, direction="clockwise")),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("Radius = view zenith angle. "
                   + ("Angle = compass azimuth of the sensor; the star marks the sun's side."
                      if compass else "Angle = relative azimuth; the sun's azimuth is at the top."))
        st.download_button("Download BRDF grid (CSV)", grid.to_csv(index=False),
                           "prosail_brdf_grid.csv", "text/csv")

# ---------------------------------------------------------------------------
# Tab 2: Location & time
# ---------------------------------------------------------------------------
with tab_loc:
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Click the map to choose a location")
        fmap = folium.Map(location=[st.session_state["lat"], st.session_state["lon"]], zoom_start=6)
        folium.Marker([st.session_state["lat"], st.session_state["lon"]],
                      tooltip="Selected location").add_to(fmap)
        clicked = st_folium(fmap, height=430, use_container_width=True,
                            returned_objects=["last_clicked"], key="map")
        last = (clicked or {}).get("last_clicked")
        if last and (round(last["lat"], 5), round(last["lng"], 5)) != (
                round(st.session_state["lat"], 5), round(st.session_state["lon"], 5)):
            st.session_state["lat"], st.session_state["lon"] = last["lat"], last["lng"]
            st.rerun()

    with right:
        lat, lon = st.session_state["lat"], st.session_state["lon"]
        tz = local_timezone(lat, lon)
        st.subheader("Date and time")
        st.write(f"**Location:** {lat:.4f}°, {lon:.4f}°  \n**Time zone:** {tz}")
        st.date_input("Date", key="obs_date")
        st.time_input("Local time", key="obs_time", step=900)
        sun = solar_position(lat, lon, datetime.combine(st.session_state["obs_date"],
                                                        st.session_state["obs_time"]), tz=tz)
        m = st.columns(2)
        m[0].metric("Solar zenith", f"{sun.sza:.1f}°")
        m[1].metric("Solar azimuth", f"{sun.saa:.1f}°")
        if sun.sza > MAX_ZENITH:
            st.warning(f"The sun is {'below the horizon' if sun.sza >= 90 else 'too low'} "
                       f"(SZA > {MAX_ZENITH:g}°) for PROSAIL.")
        st.button("Use this sun position in the simulator", type="primary",
                  disabled=sun.sza > MAX_ZENITH, on_click=apply_sun, args=(sun.sza, sun.saa))

    st.subheader("Through the day and the year")
    factor, index = st.session_state["factor"], st.session_state["index"]
    day_col, year_col = st.columns(2)
    with day_col:
        daily = cached_daily_index(params, lat, lon, st.session_state["obs_date"], factor, index)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily["time_local"], y=daily["sza"], name="Solar zenith (°)"))
        fig.add_trace(go.Scatter(x=daily["time_local"], y=daily["value"], name=f"Nadir {index}",
                                 yaxis="y2"))
        fig.add_vline(x=sun.time_local, line_dash="dot", line_color="grey")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                          title=f"Nadir {index} ({factor}) through the day",
                          yaxis=dict(title="Solar zenith (°)", range=[0, 90]),
                          yaxis2=dict(title=index, overlaying="y", side="right"),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    with year_col:
        noon = cached_noon_sza(lat, lon, st.session_state["obs_date"].year)
        fig = px.line(noon, x="date", y="min_sza",
                      labels={"date": "", "min_sza": "Solar zenith at solar noon (°)"},
                      title="Smallest solar zenith of each week")
        fig.add_vline(x=pd.Timestamp(st.session_state["obs_date"]), line_dash="dot", line_color="grey")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Tab 3: Growth stages
# ---------------------------------------------------------------------------
with tab_stage:
    stages = cached_stages()
    if stages is None:
        st.warning(f"Growth-stage table not found: {DATA_FILE}")
        st.stop()

    crop = st.selectbox("Crop", sorted(stages["crop"].unique()))
    table = stages[stages["crop"] == crop]
    labels = {r.zadoks: f"Z{r.zadoks} – {r.stage_name}" for r in table.itertuples()}
    pick = st.columns([2, 1, 1])
    zadoks = pick[0].selectbox("Zadoks stage", list(labels), format_func=labels.get)
    lai_level = pick[1].radio("LAI", LAI_LEVELS, index=1, horizontal=True,
                              format_func=lambda s: s.split("_")[1])
    row = table[table["zadoks"] == zadoks].iloc[0]
    stage_p, defaulted = stage_params(row, lai_level, defaults=params)
    pick[2].button("Load into simulator", type="primary", on_click=apply_params, args=(stage_p,))

    shown = {k: v for k, v in stage_p.to_dict().items() if k not in ("soil_scale",)}
    st.dataframe(pd.DataFrame([shown]), hide_index=True, width="stretch")
    if defaulted:
        st.caption("No sourced value in the table for: " + ", ".join(defaulted)
                   + ". The current sidebar values are used for these.")
    meta = []
    if "plant_pop_per_m2" in row and pd.notna(row["plant_pop_per_m2"]):
        meta.append(f"**Plant population:** {row['plant_pop_per_m2']:g} plants/m² "
                    "(metadata only; PROSAIL has no plant-density input)")
    for col in [c for c in table.columns if c.startswith("source")]:
        if pd.notna(row.get(col)) and str(row[col]).strip():
            meta.append(f"**{col.replace('source_', 'Source – ').replace('_', ' ')}:** {row[col]}")
    if pd.notna(row.get("notes")) and str(row["notes"]).strip():
        meta.append(f"**Notes:** {row['notes']}")
    st.markdown("  \n".join(meta))

    st.subheader("Spectral response across stages")
    st.caption(f"Geometry from the Simulator tab: SZA {st.session_state['sza']:g}°, "
               f"VZA {st.session_state['vza']:g}°, RAA {st.session_state['raa']:g}°; "
               f"factor {st.session_state['factor']}.")
    factor, index = st.session_state["factor"], st.session_state["index"]
    spectra, index_rows, no_lai = [], [], []
    for r in table.itertuples():
        stage_row = table[table["zadoks"] == r.zadoks].iloc[0]
        if pd.isna(stage_row["lai_typ"]):
            no_lai.append(f"Z{r.zadoks}")
        for level in LAI_LEVELS:
            # Only plot sourced LAI values; a blank LAI would silently fall back to the sidebar
            if pd.isna(stage_row[level]):
                continue
            p_level, _ = stage_params(stage_row, level, defaults=params)
            s = cached_spectrum(p_level, st.session_state["sza"], st.session_state["vza"],
                                st.session_state["raa"])[factor]
            index_rows.append({"zadoks": r.zadoks, "level": level, "value": compute_index(index, s)})
            if level == "lai_typ":
                spectra.append(pd.DataFrame({"wavelength": WAVELENGTHS, "reflectance": s,
                                             "stage": labels[r.zadoks]}))
    sc, ic = st.columns([3, 2])
    with sc:
        fig = px.line(pd.concat(spectra), x="wavelength", y="reflectance", color="stage",
                      color_discrete_sequence=px.colors.sequential.Viridis,
                      labels={"wavelength": "Wavelength (nm)", "reflectance": "Reflectance factor"})
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with ic:
        idx = (pd.DataFrame(index_rows).pivot(index="zadoks", columns="level", values="value")
               .reindex(columns=list(LAI_LEVELS)).reset_index())
        fig = go.Figure([
            go.Scatter(x=idx["zadoks"], y=idx["lai_max"], line=dict(width=0), showlegend=False,
                       hoverinfo="skip"),
            go.Scatter(x=idx["zadoks"], y=idx["lai_min"], fill="tonexty", line=dict(width=0),
                       fillcolor="rgba(27,120,55,0.2)", name="LAI min–max"),
            go.Scatter(x=idx["zadoks"], y=idx["lai_typ"], mode="lines+markers",
                       line=dict(color="#1b7837"), name="LAI typical"),
        ])
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10),
                          title=f"{index} by Zadoks stage", xaxis_title="Zadoks code",
                          yaxis_title=index, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    st.caption("Spectra use the typical LAI; the index panel shows min, typical and max where sourced. "
               "Other inputs without a sourced value use the sidebar."
               + (f" No sourced typical LAI for {', '.join(no_lai)}, so these stages are not plotted."
                  if no_lai else ""))

    with st.expander("Full parameter table and sources"):
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption(f"Source file: {DATA_FILE.relative_to(DATA_FILE.parents[2])}")
