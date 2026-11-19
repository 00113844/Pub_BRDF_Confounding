# pyprosail (vendored, patched)

PROSAIL (PROSPECT-5B leaf model + 4SAIL canopy model, Fortran by J.-B. Féret and
W. Verhoef) with a Python interface. This is a patched copy of
[EOA-team/PyProSAIL](https://github.com/EOA-team/PyProSAIL) (originally
[robintw/PyProSAIL](https://github.com/robintw/PyProSAIL)), vendored into the
perennial-ryegrass BRDF project. See [PATCHES.md](PATCHES.md) for every change.

```python
import pyprosail

res = pyprosail.run_all(
    n=1.5, cab=40, car=8, cbrown=0, cw=0.01, cm=0.009, psoil=0.5,
    lai=2.5, hspot=0.01, tts=30, tto=10, psi=0,
    typelidf=2, lidfa=60, lidfb=0,
)
res.wavelength   # 400..2500 nm, index = wavelength - 400
res.rsot         # bi-directional reflectance factor (direct sun, hotspot)
res.resv         # sun + sky weighted directional reflectance (upstream output)

pyprosail.run(...)  # upstream API: (2101, 2) array of [wavelength_nm, resv]
```

Angles are in degrees. `psi` is the relative azimuth between sun and sensor;
`psi = 0` is the hotspot (backscatter). Any `psi` is wrapped onto [0, 180].

## Building

Needs a Fortran and C compiler. On Windows, use MSYS2 UCRT64
(`pacman -S mingw-w64-ucrt-x86_64-gcc-fortran`) with
`<msys64>\ucrt64\bin` on `PATH`. The build uses meson-python and
`numpy.f2py` (NumPy >= 2), and links the gfortran runtime statically on Windows.

## Licence and citation

The Python interface is LGPL-3.0-or-later ([COPYING.LESSER](COPYING.LESSER),
[COPYING](COPYING)). The PROSAIL Fortran code is by Jean-Baptiste Féret, based on
code by Wout Verhoef; see the header of `src/fortran/PyPROSAIL.f90`.
Cite PyProSAIL as in [CITATION](CITATION), and PROSAIL as Jacquemoud et al.
(2009), Remote Sensing of Environment 113, S56–S66, doi:10.1016/j.rse.2008.01.026.
