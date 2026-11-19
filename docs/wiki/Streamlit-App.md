# Streamlit App – PROSAIL BRDF Explorer

[← Home](Home.md)

```bash
uv run streamlit run app/streamlit_app.py                           # http://localhost:8501
uv run streamlit run app/streamlit_app.py --server.address localhost # only reachable from this computer
```

The app lets you generate PROSAIL spectra and BRDFs interactively. You can set the sun from a real place and time, and load literature parameters for a crop growth stage.

## Layout

### Sidebar – model inputs

| Section | Controls |
|---|---|
| Leaf (PROSPECT-5B) | N, chlorophyll, carotenoids, brown pigment, water, dry matter |
| Canopy (4SAIL) | LAI. Leaf angle distribution: either **Ellipsoidal** (one slider for the mean leaf angle) or **Verhoef two-parameter** (a and b; the app warns if \|a\| + \|b\| > 1). Hotspot |
| Soil | Moisture mix (0 = wet, 1 = dry), brightness multiplier |
| Output | Reflectance factor (`resv`, `rsot`, `rdot`, `rsdt`, `rddt`) and vegetation index |

Hover over the index selector to see the formulas. See [Geometry and Reflectance Factors](Geometry-and-Reflectance-Factors.md) for which factor to choose.

### Tab 1 – Simulator

- **Geometry inputs:**
  - Solar zenith.
  - Solar azimuth. This only rotates the polar plot in compass mode.
  - View zenith.
  - Relative azimuth (0° = hotspot side).
- **Spectrum:** reflectance from 400 to 2500 nm for the chosen factor. Tick *Show all reflectance factors* to overlay all five. The metric shows the chosen index. **Download spectrum (CSV)** saves the wavelength and all five factors.
- **BRDF polar plot:** the index over the whole view hemisphere. Radius is view zenith (0–80°).
  - *Angle step* sets the grid resolution: 5, 10 or 15°.
  - *Orientation* has two modes:
    - **Relative:** the sun's azimuth is at the top.
    - **Compass:** North is at the top, and the plot is rotated by the solar azimuth.
  - The gold star marks the hotspot.
  - Hover over a cell to see its values. **Download BRDF grid (CSV)** saves `vza`, `raa` and `value`.

### Tab 2 – Location & time

1. **Click the map** to set latitude and longitude. The default is Perth. The time zone is looked up automatically.
2. Choose a **date** and **local time** (15-minute steps).
3. The tab shows the **solar zenith and azimuth** (pvlib). It warns if the sun is below the horizon or above 85° zenith.
4. **Use this sun position in the simulator** copies the zenith and azimuth into Tab 1 and switches the polar plot to compass orientation.
5. Two charts:
   - **Through the day:** solar zenith and the nadir index (chosen factor) every 15 minutes.
   - **Through the year:** the smallest solar zenith of each week at that location. Use it to see the seasonal range of illumination.

### Tab 3 – Growth stages

1. Pick the **crop** and the **Zadoks stage**. The data comes from [`data/crop_parameters/growth_stages.csv`](../../data/crop_parameters/growth_stages.csv).
2. Choose **LAI min / typ / max**.
3. The table shows the parameters that will be loaded. A caption lists inputs with no sourced value; those keep the current sidebar values. Plant population, sources and notes are shown underneath. Plant population is metadata only, because PROSAIL has no density input.
4. **Load into simulator** pushes the values into the sidebar. Values outside the slider ranges are clipped.
5. **Spectral response across stages:**
   - typical-LAI spectra for every stage that has a sourced LAI;
   - the index against Zadoks code, with a min–max LAI band.
   - Both use the geometry and factor from Tab 1. Stages without a sourced LAI are listed and not plotted, so you never see a curve that silently used the sidebar LAI.
6. Expand **Full parameter table and sources** to see every column.

See [Growth-Stage Database](Growth-Stage-Database.md).

## How it works inside

- **Session state.**
  - Every sidebar widget has a key in `st.session_state` (`p_N`, `p_cab`, …, `sza`, `saa`, `vza`, `raa`, `lat`, `lon`, …), initialised once from `CanopyParams()` defaults.
  - Buttons that change other widgets (*Use this sun position*, *Load into simulator*) do so in `on_click` callbacks. Callbacks run before the next script run, which is the only time Streamlit allows widget values to be set from code.
- **The engine.** `current_params()` builds a `CanopyParams` from the sidebar. All model runs go through `prosail_engine.simulate` and `brdf_grid`, so the azimuth wrapping and angle limits are the same as in the paper figures.
- **Caching.** Model runs are wrapped in `st.cache_data`, keyed on the frozen `CanopyParams` and the geometry:

  | Cached function | What it holds | Max entries |
  |---|---|---|
  | `cached_spectrum` | single spectra | 64 |
  | `cached_grid` | BRDF grids | 32 |
  | `cached_daily_index` | daily curves | 16 |
  | `cached_noon_sza` | yearly curve | – |
  | `cached_stages` | the CSV | – |

  Changing a slider back to an earlier value is instant.
- **Cost.** One model run takes about 0.8 ms. A 5° grid is 17 view zeniths × 37 unique azimuths (mirror azimuths are reused), about 0.5 s. The daily curve is up to 96 runs.
- **Map.** `streamlit-folium` returns only `last_clicked`, to avoid rerunning on every pan or zoom. A click that differs from the stored location updates `lat`/`lon` and triggers one rerun.
- **Polar plot.** A Plotly `Barpolar` trace with one bar per grid cell: `base = vza − step/2`, length = step, colour = value. In compass mode, `theta = (raa + saa) mod 360`.

## Extending the app

- **New index:** add it to `publication_spectral_data/indices.py` (see [PROSAIL Engine](PROSAIL-Engine.md#vegetation-indices--indicespy)).
- **New crop:** add rows to `growth_stages.csv`. The crop selector picks it up automatically.
- **New input:** add a field to `CanopyParams`, a range to `RANGES`, and a slider in the sidebar.
- After changing `growth_stages.csv` while the app is running, clear the cache (menu → *Clear cache*) or restart the app.

Next: [Growth-Stage Database](Growth-Stage-Database.md).
