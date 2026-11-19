# Growth-Stage Database

[← Home](Home.md)

**Files:** [`data/crop_parameters/growth_stages.csv`](../../data/crop_parameters/growth_stages.csv) (the data), [`sources.md`](../../data/crop_parameters/sources.md) (full citations and where each value came from), and [`README.md`](../../data/crop_parameters/README.md) (column units).

**Code:** `publication_spectral_data.crop_params`.

## Purpose

The table gives PROSAIL inputs that are realistic for a crop at a given Zadoks growth stage, so simulations reflect field conditions and not arbitrary defaults. It currently holds **wheat** (*Triticum aestivum*) at 11 stages: Z13, Z21, Z25, Z30, Z32, Z39, Z55, Z65, Z75, Z85 and Z92.

## Schema

One row per `crop` × `zadoks`. The columns are:

- **identification:** `crop`, `zadoks`, `stage_name`;
- **LAI:** `lai_min`, `lai_typ`, `lai_max`;
- **leaf angle:** `typelidf`, `lidfa`, `lidfb`, `mean_leaf_angle_deg`;
- **agronomy:** `plant_pop_per_m2` (metadata only);
- **leaf:** `cab`, `car`, `cw`, `cm`, `N`, `cbrown`;
- **canopy:** `hspot`, `psoil`;
- **provenance:** `source_lai`, `source_leaf_angle`, `source_plant_pop`, `source_cab`, `source_other`, `notes`.

Units match [`CanopyParams`](PROSAIL-Engine.md#canopyparams).

## Provenance rules

- **Every number has a source.** Peer-reviewed sources are cited by DOI, and each DOI was checked against Crossref. Grey literature is cited by URL: AHDB Wheat growth guide 2018, GRDC GrowNotes Wheat Western 2015.
- **Blank means unknown.** Blank cells are never filled with estimates. The loader reports which inputs had no value, and the app keeps the sidebar values for those.
- **`notes` flags how each value was obtained:**
  - `[CALC]` – calculated from sourced numbers (e.g. `car = cab/5`; `hspot = flag-leaf width / canopy height`);
  - `[CROP-LEVEL]` – a season-wide value, not specific to the stage;
  - `[STAGE-MAPPED]` – the source gave a stage name or date, and the Zadoks code was assigned during compilation;
  - `[BRACKETED]`, `[DATE-MAPPED]` – taken from adjacent stages or matched by calendar date.

## Main sources (wheat)

| Source | Used for |
|---|---|
| Xing et al. 2021, *Big Earth Data*, doi:10.1080/20964471.2021.1918909 | LAI and chlorophyll ranges at early jointing, late jointing, heading and milk (Z30, Z32, Z55, Z75) |
| O'Leary et al. 2015, *Global Change Biology*, doi:10.1111/gcb.12830 | Australian rain-fed LAI at anthesis (Z65); measured plant density |
| AHDB 2018 Wheat growth guide (UK) | Green area index benchmarks, canopy heights, plant population benchmark |
| Hosoi et al. 2009, *J. Agric. Meteorol.*, doi:10.2480/agrmet.65.3.6 | Lidar-measured mean leaf angle by stage |
| Danner et al. 2019, *Remote Sensing*, doi:10.3390/rs11101150 | Season-wide Cab, water, dry matter, brown pigment |
| Jiang et al. 2018, *Plant Methods*, doi:10.1186/s13007-018-0291-x | PROSPECT N, Cab:Car ratio |
| Wang et al. 2022, *Front. Plant Sci.*, doi:10.3389/fpls.2022.990287 | Flag-leaf width (for the hotspot) |
| GRDC 2015; Anderson et al. 2004, doi:10.1071/AR03248 | Western Australian plant population |

## Known gaps and caveats

- **Missing typical LAI** at Z13, Z21, Z25, Z39 and Z85. Missing pigment, water and brown-pigment values at Z85 and Z92.
- **Season-wide values** are used for `cw`, `cm`, `N`, and for `cab` and leaf angle at several stages.
- **Mostly non-Australian LAI.** LAI comes mostly from an irrigated Chinese trial and UK benchmarks. Some of it is green *area* index, which includes stems. Western Australian dryland crops will usually sit at or below `lai_min`.
- **Leads to fill the gaps:**
  - Danner et al. 2019, supplementary Table S1 (per-date values; has to be downloaded by hand);
  - Siddique et al. 1989, doi:10.1071/AR9890473 (Western Australian green area by stage).

## Python API

```python
from publication_spectral_data.crop_params import load_growth_stages, stage_params

table = load_growth_stages()          # sorted; checks columns and lai_min ≤ lai_typ ≤ lai_max
row = table[(table.crop == "wheat") & (table.zadoks == 55)].iloc[0]
params, defaulted = stage_params(row, lai_level="lai_max", defaults=CanopyParams())
# params: CanopyParams with sourced values; defaulted: names that fell back to `defaults`
```

## Adding data

1. **Add rows** with the same header, for a new stage or a new crop such as `perennial_ryegrass`. Use Zadoks codes, or document the scale you use in `notes`.
2. **Fill only sourced values.** Put the DOI or URL in the matching `source_*` column and flag derived values in `notes`.
3. **Add the full citation** to `sources.md`, with the table, figure or page each value came from.
4. **Check the file loads:** `uv run python -c "from publication_spectral_data.crop_params import load_growth_stages; print(load_growth_stages().tail())"`.
5. **Restart the app**, or clear its cache.

Next: [Validation and Tests](Validation-and-Tests.md).
