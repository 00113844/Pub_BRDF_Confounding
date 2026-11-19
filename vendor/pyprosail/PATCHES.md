# Changes against upstream PyProSAIL

Upstream: https://github.com/EOA-team/PyProSAIL, HEAD `0470fd7`
(last change under `pyprosail/`: `c635f07`, 2023-03-03).

The review behind these changes is in
[docs/prosail_implementation_review.md](../../docs/prosail_implementation_review.md).

## Fortran

Unchanged, byte for byte: `MODULE_PRO4SAIL.f90`, `dataSpec_P5B.f90`, `LIDF.f90`,
`dladgen.f`, `PRO4SAIL.f90`, `prospect_5B.f90`, `tav_abs.f90`, `volscatt.f90`.
These match the PROSAIL code in the hsdar R package apart from type spellings.

`PyPROSAIL.f90` (subroutine `run`):

1. Returns `resv`, `rsot`, `rdot`, `rsdt` and `rddt`. Upstream returned `resv` only.
2. New arguments `use_soil` and `rsoil_in`: when `use_soil = 1`, `rsoil_in` is
   used as the soil spectrum. This is the custom-soil branch of hsdar's
   `main_PROSAIL.f90`, with an explicit flag instead of the `-9999.9` sentinel.
3. Deallocation is guarded with `allocated()`, as in hsdar.
4. Unused variables `ihot` and `ii` removed.

## Python wrapper (`pyprosail/__init__.py`)

1. **LIDF check fixed.** Upstream rejected `lidfa + lidfb > 1`; Verhoef's
   condition is `|lidfa| + |lidfb| <= 1`. Pairs such as (0.5, -0.8) passed the
   old check and gave negative LIDF weights.
2. **psi wrapped onto [0, 180].** `volscatt` assumes 0 <= psi <= 180, but the
   hotspot term only uses cos(psi); upstream evaluated psi = 350 differently from
   psi = 10 (up to about 23 % in single scattering at tts = 40, tto = 60).
3. **Input validation.** tts and tto must be in [0, 90) (90 divides by
   cos = 0); psoil in [0, 1]; lidfa in [0, 90] for typelidf 2; n >= 1;
   non-negative contents, LAI and hotspot; all inputs finite.
4. **New `run_all()`** returns a `ProsailResult` with every reflectance factor and
   accepts an optional `soil_spectrum`. `run()` keeps the upstream signature and
   (2101, 2) output.
5. **Import fixed:** `from ._prosail_model import run` (upstream imported a
   top-level `_prosail_model`, which breaks with the Makefile build).
6. Docstrings corrected: argument names, units (nm), the fact that `resv`
   is not a pure BRF, and that predefined LIDF tuples must be unpacked.

## Build

`setup.py` (numpy.distutils, removed in NumPy 2 / Python 3.12), `Makefile`,
`appveyor.yml` and the committed `pyprosail.egg-info/` are replaced by
`pyproject.toml` + `meson.build` (meson-python, `numpy.f2py`) with a hand-written
f2py signature file `src/fortran/_prosail_model.pyf`.
