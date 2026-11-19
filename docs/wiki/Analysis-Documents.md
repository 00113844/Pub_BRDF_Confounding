# Analysis Documents

[← Home](Home.md)

Both documents run Python chunks in the `hyperspectral-brdf` Jupyter kernel, which is backed by `.venv`. Register the kernel once:

```bash
.venv\Scripts\python.exe -m ipykernel install --user --name hyperspectral-brdf --display-name "Python (.venv BRDF)"
```

## `BRDF.qmd` – NDVI BRDF of a grass canopy

```bash
quarto render BRDF.qmd
```

What it does:

1. Defines the reference ryegrass canopy as a `CanopyParams`:
   - LAI 2.5, mean leaf angle 60° (erectophile), Cab 40 µg/cm², hotspot 0.01;
   - psoil 0.5, soil brightness 1.
2. Fixes SZA at 30° and builds a 5° grid of VZA 0–80° and RAA 0–360°.
3. Calls `brdf_grid` twice, for `rsot` (BRF) and for `resv` (sun + sky). NDVI uses R670 and R800.
4. Plots two polar contour maps on a shared colour scale. The sun's azimuth is at the top, and a star marks the hotspot.
5. Prints a table of NDVI at nadir, plus the minimum and maximum.

Reference output (SZA 30°):

| Factor | NDVI at nadir | Min | Max |
|---|---|---|---|
| `rsot` | 0.858 | 0.765 | 0.965 |
| `resv` | 0.871 | 0.794 | 0.955 |

For both factors, the minimum NDVI is at the hotspot (VZA 30°, RAA 0°), where no shadows are visible and red reflectance is relatively high. The maximum is at grazing forward scatter (VZA 80°, RAA 180°), where the line of sight crosses the most foliage and sees mostly shaded leaves.

## `article.qmd` – manuscript

```bash
quarto use template quarto-journals/elsevier   # once
quarto render article.qmd --to elsevier-pdf
```

This is the manuscript scaffold: Introduction, Methods (simulation framework, geometry design), Results and Discussion. References are in `references.bib`.

When writing the Methods, state:

- the model versions (PROSPECT-5B, 4SAIL, patched PyProSAIL `1.0.2+brdf.1`);
- the reflectance factor used;
- the azimuth convention;
- the zenith limits.

See the recommendations in [../prosail_implementation_review.md](../prosail_implementation_review.md#5-recommendations-for-the-manuscript).

## Conventions for new analyses

- **Keep the analysis in Quarto.** Move reusable logic into `src/publication_spectral_data/`.
- **Use the engine.** Go through `prosail_engine`, never through the raw packages.
- **Name bands explicitly.** Comment the wavelength-to-index mapping whenever you extract bands.
- **Record geometry choices.** If you change a geometry grid, write down why and what it means for interpretation.
- **Save outputs** to `results/figures` and `results/logs`.

Next: [Troubleshooting](Troubleshooting.md).
