# Perennial Ryegrass BRDF – Project Wiki

This wiki explains how the repository works: the PROSAIL model and the patched Fortran engine, the Python package built around it, the Streamlit app, the crop growth-stage database, the analysis documents and the validation scripts.

The repository supports a journal article on how bidirectional reflectance (BRDF) and sun/view geometry change measured canopy reflectance in perennial ryegrass, and what that means for estimating biomass and crude protein.

## Pages

| Page | What it covers |
|---|---|
| [Getting Started](Getting-Started.md) | Installing the toolchain, Python and R environments; running everything |
| [Architecture](Architecture.md) | Repository layout, how the pieces connect, data flow |
| [PROSAIL Engine](PROSAIL-Engine.md) | The model, the vendored PyProSAIL build, the Python API, parameters and indices |
| [Geometry and Reflectance Factors](Geometry-and-Reflectance-Factors.md) | Angle conventions, the hotspot, `rsot` vs `resv`, solar position |
| [Streamlit App](Streamlit-App.md) | The PROSAIL BRDF Explorer, tab by tab, and how it works inside |
| [Growth-Stage Database](Growth-Stage-Database.md) | The wheat parameter table, its sources and how to extend it |
| [Validation and Tests](Validation-and-Tests.md) | Test suite, cross-checks against other PROSAIL implementations, key results |
| [Analysis Documents](Analysis-Documents.md) | `BRDF.qmd`, `article.qmd` and rendering with Quarto |
| [Troubleshooting](Troubleshooting.md) | Common errors and fixes |

## Quick start

```bash
uv sync                                    # needs gfortran on PATH the first time (see Getting Started)
uv run streamlit run app/streamlit_app.py  # interactive explorer at http://localhost:8501
uv run pytest                              # 27 tests
```

## Five things to know

1. **The model is PROSAIL** (PROSPECT-5B leaf model + 4SAIL canopy model). The code is a patched copy of PyProSAIL's Fortran in `vendor/pyprosail`. Its physics is identical to the hsdar R package.
2. **Spectra run from 400 to 2500 nm in 1 nm steps**, so `index = wavelength − 400`.
3. **Relative azimuth `raa = 0°` is the hotspot**, with the sensor on the sun's side. The engine wraps any `raa` onto 0–180°, because the model assumes that range.
4. **`rsot` and `resv` are different quantities.** `rsot` is the BRF under direct sun. `resv` is a sun-plus-sky mix, closer to a field measurement. Always say which one you use.
5. **Zenith angles must stay below 90°.** The engine allows up to 85° and the app plots up to 80°.

The detailed review of the PROSAIL implementations is in [../prosail_implementation_review.md](../prosail_implementation_review.md).
