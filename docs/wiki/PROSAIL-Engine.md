# PROSAIL Engine

[← Home](Home.md)

## The model in brief

PROSAIL couples two radiative transfer models:

- **PROSPECT-5B** (Féret et al., 2008) simulates leaf reflectance and transmittance from 400 to 2500 nm. Its inputs are the leaf structure (`N`), the pigments (`cab`, `car`, `cbrown`), water (`cw`) and dry matter (`cm`).
- **4SAIL** (Verhoef et al., 2007) is a four-stream model of a horizontally uniform canopy. It scatters the leaf optics through a canopy described by:
  - LAI;
  - a leaf inclination distribution (LIDF);
  - a hotspot parameter;
  - a soil background.

It returns several reflectance factors for a given sun and view direction.

Reference: Jacquemoud et al. (2009), *Remote Sensing of Environment* 113, S56–S66, doi:10.1016/j.rse.2008.01.026.

## Layer 1 – `vendor/pyprosail`

A patched copy of [EOA-team/PyProSAIL](https://github.com/EOA-team/PyProSAIL), upstream HEAD `0470fd7`.

**Fortran sources** are in `src/fortran/`:

| File | Content |
|---|---|
| `MODULE_PRO4SAIL.f90` | Shared module variables (state kept between calls) |
| `dataSpec_P5B.f90` | Spectral data: refractive index, absorption coefficients, Es/Ed light spectra, dry and wet soil |
| `prospect_5B.f90`, `tav_abs.f90` | PROSPECT-5B leaf model |
| `LIDF.f90`, `dladgen.f` | Leaf angle distributions: Campbell ellipsoidal (type 2), Verhoef two-parameter (type 1) |
| `volscatt.f90` | Volume scattering functions |
| `PRO4SAIL.f90` | 4SAIL canopy model |
| `PyPROSAIL.f90` | Entry point `run`. **The only patched Fortran file:** it returns all five factors and takes an optional soil spectrum |

**Build:**

- `meson.build` runs `numpy.f2py` on the hand-written signature file `_prosail_model.pyf`. Writing the signature by hand means f2py produces exactly one C file.
- The C file is compiled together with the Fortran into `pyprosail/_prosail_model.*.pyd`.
- On Windows, the gfortran runtime is linked statically (`-static`).

**Python API:**

```python
import pyprosail

res = pyprosail.run_all(n, cab, car, cbrown, cw, cm, psoil, lai, hspot,
                        tts, tto, psi, typelidf, lidfa, lidfb, soil_spectrum=None)
res.wavelength, res.resv, res.rsot, res.rdot, res.rsdt, res.rddt   # each (2101,)
res.as_array("rsot")                                               # (2101, 2) [nm, value]

pyprosail.run(...)   # upstream-compatible: (2101, 2) array of [wavelength, resv]
```

`run_all` validates its inputs and raises `ValueError` if any check fails:

- `typelidf` must be 1 or 2;
- type 1 requires `|lidfa| + |lidfb| ≤ 1`;
- type 2 requires `0 ≤ lidfa ≤ 90`;
- `n ≥ 1`;
- contents, LAI and hotspot must be ≥ 0;
- `psoil` must be in [0, 1];
- `0 ≤ tts, tto < 90`;
- every value must be finite;
- `soil_spectrum`, if given, must have 2101 values in [0, 1].

It also wraps `psi` onto [0, 180]. See [PATCHES.md](../../vendor/pyprosail/PATCHES.md) for the full list of fixes.

**Changing the Fortran.** Edit the files, then run `uv sync --reinstall-package pyprosail` with gfortran on `PATH`.

## Layer 2 – `publication_spectral_data.prosail_engine`

### `CanopyParams`

A frozen dataclass of model inputs. The defaults are the reference ryegrass canopy.

| Field | Default | Unit | Meaning | Typical range |
|---|---|---|---|---|
| `N` | 1.5 | – | Leaf structure (number of layers) | 1–3 |
| `cab` | 40 | µg/cm² | Chlorophyll a+b | 0–100 |
| `car` | 8 | µg/cm² | Carotenoids | 0–30 |
| `cbrown` | 0 | – | Brown (senescent) pigment | 0–1 |
| `cw` | 0.01 | cm | Equivalent water thickness | 0.001–0.06 |
| `cm` | 0.009 | g/cm² | Dry matter per leaf area | 0.001–0.03 |
| `lai` | 2.5 | m²/m² | Leaf area index | 0–10 |
| `typelidf` | 2 | – | 2 = ellipsoidal (Campbell), 1 = Verhoef two-parameter | – |
| `lidfa` | 60 | ° or – | Type 2: mean leaf angle (0 = horizontal, 90 = vertical). Type 1: parameter a | – |
| `lidfb` | 0 | – | Type 1 only: bimodality parameter b | – |
| `hspot` | 0.01 | – | Hotspot size, about leaf width / canopy height | 0–1 |
| `psoil` | 0.5 | – | Soil mix: 0 = wet, 1 = dry built-in soil | 0–1 |
| `soil_scale` | 1.0 | – | Brightness multiplier on the mixed soil | 0–2 |

Helpers: `CanopyParams.from_mapping(dict)`, which ignores unknown keys and blanks; `.to_dict()`; and `.updated(**changes)`.

### `simulate(params, sza, vza, raa, backend="pyprosail")`

Returns `{"wavelength", "resv", "rsot", "rdot", "rsdt", "rddt"}`.

- `sza` and `vza` must be in [0, 85]°.
- `raa` can be any angle; it is wrapped onto [0, 180].

### `brdf_grid(params, sza, vza_values, raa_values, factor="rsot", index="NDVI", wavelength=None, backend=...)`

Runs `simulate` over a grid of view angles and returns a tidy DataFrame with columns `vza`, `raa` and `value`. The value is the index computed from `factor`, or the reflectance at `wavelength` when `index=None`.

- `raa` keeps the range you passed (for example 0–360 for polar plots).
- Mirror-image azimuths (`raa` and `360 − raa`) are simulated once and reused. A 17 × 72 grid therefore costs about 17 × 37 model runs, at roughly 0.8 ms each.

### Backends

| Backend | Implementation | Use |
|---|---|---|
| `"pyprosail"` (default) | Patched Fortran | Everything |
| `"prosail_py"` | jgomezdans `prosail` 2.0.5 (pure Python, PROSPECT-5) | Cross-checks and fallback. Needs the dev group |

For `prosail_py`, the engine computes `resv` itself with the same sky-light formula, using that package's Es/Ed spectra. The two backends agree within about 4e-4 RMSD (see [Validation and Tests](Validation-and-Tests.md)).

### Soil

`builtin_soils()` reads the Fortran's own dry (`Rsoil1`) and wet (`Rsoil2`) soil spectra by running the model with LAI = 0, since 4SAIL then returns the soil itself. When `soil_scale ≠ 1`, the engine passes `soil_scale × (psoil·dry + (1−psoil)·wet)`, clipped to [0, 1], as a custom soil spectrum.

## Vegetation indices – `indices.py`

Indices use single 1 nm bands, with no sensor spectral response.

| Index | Formula |
|---|---|
| NDVI | (R800 − R670) / (R800 + R670) |
| EVI | 2.5 (R800 − R670) / (R800 + 6 R670 − 7.5 R470 + 1) |
| SAVI | 1.5 (R800 − R670) / (R800 + R670 + 0.5) |
| NDRE | (R800 − R720) / (R800 + R720) |
| GNDVI | (R800 − R550) / (R800 + R550) |
| MTCI | (R754 − R709) / (R709 − R681) (Dash & Curran, 2004) |

`compute_index(name, spectrum)` works on a single spectrum `(2101,)` or a stack `(..., 2101)`. To add an index, write a function of the spectrum and register it in `INDICES` and `INDEX_FORMULAS`. The app picks it up automatically.

## Limitations to keep in mind

- **Turbid-medium canopy.** The canopy is horizontally uniform, with no rows, clumping or ears; stems are not modelled separately.
- **Fixed sky light.** The diffuse sky fraction in `resv` is a clear-sky empirical formula (François et al., 2002) with fixed Es/Ed spectra.
- **Not thread-safe.** The Fortran keeps its state in module variables. Parallelise with processes, not threads.

Next: [Geometry and Reflectance Factors](Geometry-and-Reflectance-Factors.md).
