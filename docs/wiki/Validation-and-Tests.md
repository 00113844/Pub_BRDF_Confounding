# Validation and Tests

[← Home](Home.md)

## Test suite

`uv run pytest` runs [`tests/test_prosail_engine.py`](../../tests/test_prosail_engine.py): 27 tests, about 10 seconds.

| Test | What it guarantees |
|---|---|
| `test_outputs_have_full_spectral_range` | Five factors, 2101 bands from 400 to 2500 nm, finite, between 0 and 1 |
| `test_upstream_run_returns_wavelength_and_resv` | `pyprosail.run()` still matches the upstream (2101, 2) output |
| `test_psi_is_wrapped` | 350 ≡ 10, −30 ≡ 30, 540 ≡ 180, 190 ≡ 170 |
| `test_invalid_inputs_raise` | Bad LIDF pairs, unknown LIDF type, leaf angle > 90, zenith = 90, psoil > 1, negative LAI, N < 1 and NaN all raise `ValueError` |
| `test_hotspot_peak_is_at_solar_direction` | The 800 nm BRF peaks at VZA = SZA in the backscatter direction |
| `test_resv_is_a_mix_of_direct_and_diffuse` | `resv` lies between `rdot` and `rsot` |
| `test_custom_soil_spectrum_matches_builtin_mix` | The custom soil path equals the built-in psoil mix |
| `test_zero_lai_returns_soil` | LAI = 0 returns the soil spectrum |
| `test_soil_scale_darkens_sparse_canopy` | The soil brightness multiplier works |
| `test_engine_rejects_near_horizontal_view` | The engine rejects VZA > 85° |
| `test_backends_agree` | Fortran and pure-Python backends agree within 2e-3 for VZA ≤ 70° |
| `test_brdf_grid_is_symmetric_about_principal_plane` | The BRDF is mirror-symmetric |
| `test_wrap_raa`, `test_ndvi_of_vegetation_is_high`, `test_solar_position_perth_summer_noon`, `test_stage_params_falls_back_to_defaults` | Helpers |

## Cross-checking PROSAIL implementations

```bash
uv run python scripts/crosscheck_prosail.py   # pass 1: writes the cases + soil, compares Python backends
Rscript scripts/crosscheck_prosail.R          # runs R prosail on the same cases
uv run python scripts/crosscheck_prosail.py   # pass 2: merges the R results
```

**Case matrix.** 3 canopies × SZA {20, 45, 60}° × VZA {0, 20, 40, 60, 80}° × RAA {0, 90, 180}° = 135 cases. The canopies are:

- ryegrass default: LAI 2.5, mean leaf angle 60°;
- sparse erect: LAI 0.8, 70°;
- dense planophile: LAI 5, 30°, hotspot 0.1.

Every implementation is given the same soil, which is the Fortran's own spectra.

**Outputs** in `results/logs/`:

| File | Content |
|---|---|
| `crosscheck_cases.csv`, `crosscheck_soil.csv` | Shared inputs (read by the R script) |
| `crosscheck_r_spectra.csv` | R output, every 10 nm |
| `crosscheck_differences.csv` | Per case and factor: maximum \|Δ\| and RMSD in VIS, red-edge, NIR and SWIR |
| `crosscheck_summary.csv` | The above, aggregated |
| `crosscheck_psi_wrap.csv` | Error from unwrapped relative azimuth |
| `crosscheck_resv_vs_rsot.csv` | Hotspot-to-forward ratios for both factors |

**Figures** in `results/figures/`: `crosscheck_spectra.png` and `crosscheck_psi_wrap.png`.

### Key results

| Comparison | Agreement | Interpretation |
|---|---|---|
| Patched PyProSAIL vs jgomezdans `prosail` (both PROSPECT-5 + 4SAIL) | RMSD ≤ 4e-4. Max \|Δ\| ≤ 8e-4 for VZA ≤ 40°, 3.3e-3 at VZA = 80° | Same model; small numerical differences that grow at grazing view |
| Patched PyProSAIL vs R `prosail` 3.2.0 (PROSPECT-PRO) | Max \|Δ\| up to 0.057 at 530–550 nm and at the 750 nm red-edge shoulder; about 1e-3 beyond 780 nm at nadir | Different leaf model (pigment absorption coefficients), not a bug. Do not mix the two in one analysis |
| Unwrapped vs wrapped relative azimuth | Up to 25% error at 670 nm | Bug in upstream PyProSAIL and jgomezdans `prosail`; fixed in the engine |

### hsdar

hsdar was not run, because it is archived on CRAN and depends on the retired `rgdal`. Instead, its Fortran was diffed against PyProSAIL's, and the two are identical apart from type spellings. All 11 spectral data arrays match value for value.

The full write-up is in [../prosail_implementation_review.md](../prosail_implementation_review.md).

Next: [Analysis Documents](Analysis-Documents.md).
