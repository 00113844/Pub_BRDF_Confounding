# Crop growth-stage parameters for PROSAIL

[growth_stages.csv](growth_stages.csv) has one row per crop and Zadoks stage. It is read by `publication_spectral_data.crop_params` and by the **Growth stages** tab of the Streamlit app. Full citations, the table or passage each value came from, and the reasons for blank cells are in [sources.md](sources.md).

## Columns and units

| Column | Unit | Meaning |
|---|---|---|
| `crop`, `zadoks`, `stage_name` | – | Crop, Zadoks decimal code (Zadoks et al., 1974) and stage name |
| `lai_min`, `lai_typ`, `lai_max` | m²/m² | Green LAI range reported for the stage. Some sources give green area index, which includes stems and sheaths |
| `typelidf`, `lidfa`, `lidfb` | –, °, – | 4SAIL leaf angle distribution. Type 2 (ellipsoidal) with `lidfa` as the mean leaf angle |
| `mean_leaf_angle_deg` | ° | Same as `lidfa`, kept for readability |
| `plant_pop_per_m2` | plants/m² | Agronomic metadata only; PROSAIL has no plant-density input |
| `cab`, `car` | µg/cm² | Leaf chlorophyll a+b and carotenoids |
| `cw` | cm (g/cm²) | Equivalent water thickness |
| `cm` | g/cm² | Leaf dry matter per area |
| `N` | – | PROSPECT leaf structure parameter |
| `cbrown` | 0–1 | Brown pigment |
| `hspot` | – | Hotspot parameter, leaf width / canopy height |
| `psoil` | 0–1 | Left blank; soil is set in the app |
| `source_*`, `notes` | – | Source of each value and how it was obtained |

## Reading the notes flags

- **[CALC]**: derived by calculation from sourced numbers (e.g. `car = cab / 5`, `hspot = leaf width / height`).
- **[CROP-LEVEL]**: a season-wide value, not specific to the stage.
- **[STAGE-MAPPED]**: the source named the stage in words or by date, and the Zadoks code was assigned during compilation.
- **[BRACKETED]** / **[DATE-MAPPED]**: taken from adjacent stages, or matched by calendar date.

**Blank cells** mean no sourced value was found. The engine then uses the current or default value and reports which inputs were filled in that way. **Do not fill blanks with estimates**; add a source instead.

## Caveats (wheat, compiled 2026-11-06)

- LAI ranges come mainly from an irrigated North China Plain trial (Xing et al., 2021) and UK benchmarks (AHDB, 2018). Australian rain-fed values are available only at Z65 (O'Leary et al., 2015). Western Australian dryland crops will usually sit near or below `lai_min`.
- `cw`, `cm`, `N` and the crop-level `cab` and leaf angle are season-wide values. The best route to stage-specific values is Danner et al. (2019), supplementary Table S1 (doi:10.3390/rs11101150), which has to be downloaded by hand. Siddique et al. (1989, doi:10.1071/AR9890473) is the best lead for Western Australian green area by stage.
- Senescing stages (Z85, Z92) lack pigment, water and brown-pigment values.
