"""
A module that allows easy running of the ProSAIL (PROSPECT + SAIL) leaf and canopy
reflectance model.

The main functions are `run`, which returns the sky-light weighted directional
reflectance as a (2101, 2) array (upstream PyProSAIL behaviour), and `run_all`,
which returns every 4SAIL reflectance factor in a `ProsailResult`.

# Copyright (C) 2013  Robin Wilson, Modifications regarding code readability and function interfaces by Lukas Valentin Graf
# Input validation, psi wrapping and the extra outputs added for the perennial
# ryegrass BRDF project; see PATCHES.md.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ._prosail_model import run as run_fortran

__all__ = [
    "run",
    "run_all",
    "ProsailResult",
    "WAVELENGTHS",
    "wrap_psi",
    "Planophile",
    "Erectophile",
    "Plagiophile",
    "Extremophile",
    "Spherical",
    "Uniform",
]

# PROSAIL output grid: 400-2500 nm at 1 nm, so index = wavelength - 400
WAVELENGTHS = np.arange(400, 2501)
_NW = WAVELENGTHS.size

# Common leaf distributions (typelidf=1: LIDFa, LIDFb)
Planophile = (1, 0)
Erectophile = (-1, 0)
Plagiophile = (0, -1)
Extremophile = (0, 1)
Spherical = (-0.35, -0.15)
Uniform = (0, 0)


@dataclass(frozen=True)
class ProsailResult:
    """All reflectance factors from one PROSAIL run, each of shape (2101,).

    * ``resv`` -- directional reflectance under sun + sky illumination:
      ``(rdot*Ed*skyl + rsot*Es*(1-skyl)) / (Ed*skyl + Es*(1-skyl))``, which is what
      upstream PyProSAIL and hsdar return. Closest to a field (HDRF) measurement.
    * ``rsot`` -- bi-directional reflectance factor (direct sun only, has the hotspot)
    * ``rdot`` -- hemispherical-directional reflectance factor (diffuse sky only)
    * ``rsdt`` -- directional-hemispherical reflectance factor (black-sky albedo)
    * ``rddt`` -- bi-hemispherical reflectance factor (white-sky albedo)
    """

    wavelength: np.ndarray
    resv: np.ndarray
    rsot: np.ndarray
    rdot: np.ndarray
    rsdt: np.ndarray
    rddt: np.ndarray

    def as_array(self, factor: str = "resv") -> np.ndarray:
        """Return a (2101, 2) array of [wavelength_nm, factor]."""
        return np.column_stack((self.wavelength, getattr(self, factor)))


def wrap_psi(psi: float) -> float:
    """Map any relative azimuth (degrees) onto [0, 180].

    4SAIL's volscatt assumes 0 <= psi <= 180 while the hotspot term only uses
    cos(psi), so e.g. psi = 350 must be evaluated as psi = 10.
    """
    return abs(psi - 360.0 * round(psi / 360.0))


def _check_finite(**values: float) -> None:
    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number, got {value}")


def _validate(n, cab, car, cbrown, cw, cm, psoil, lai, hspot, tts, tto, typelidf, lidfa, lidfb):
    if typelidf not in (1, 2):
        raise ValueError(f"typelidf must be either 1 or 2, got {typelidf}")
    if typelidf == 1 and abs(lidfa) + abs(lidfb) > 1:
        raise ValueError(
            "If typelidf is 1, |lidfa| + |lidfb| must not be greater than 1 "
            f"(got lidfa={lidfa}, lidfb={lidfb}); larger values give negative LIDF weights."
        )
    if typelidf == 2 and not 0 <= lidfa <= 90:
        raise ValueError(f"If typelidf is 2, lidfa is the mean leaf angle in [0, 90] degrees, got {lidfa}")
    if n < 1:
        raise ValueError(f"n (leaf structure) must be >= 1, got {n}")
    for name, value in (("cab", cab), ("car", car), ("cbrown", cbrown), ("cw", cw),
                        ("cm", cm), ("lai", lai), ("hspot", hspot)):
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")
    if psoil is not None and not 0 <= psoil <= 1:
        raise ValueError(f"psoil must be in [0, 1] (0 = wet, 1 = dry), got {psoil}")
    # 4SAIL divides by cos(zenith): 90 degrees gives Inf/NaN
    for name, value in (("tts", tts), ("tto", tto)):
        if not 0 <= value < 90:
            raise ValueError(f"{name} must be in [0, 90) degrees, got {value}")


def run_all(
    n: float,
    cab: float,
    car: float,
    cbrown: float,
    cw: float,
    cm: float,
    psoil: float,
    lai: float,
    hspot: float,
    tts: float,
    tto: float,
    psi: float,
    typelidf: int,
    lidfa: int | float,
    lidfb: int | float,
    soil_spectrum: np.ndarray | None = None,
) -> ProsailResult:
    """
    Runs the ProSAIL model and returns every 4SAIL reflectance factor.

    Arguments:

      * ``n`` -- Structure co-efficient (>= 1)
      * ``cab`` -- Chlorophyll content (ug per cm^2)
      * ``car`` -- Carotenoid content (ug per cm^2)
      * ``cbrown`` -- Brown pigment content (arbitrary units)
      * ``cw`` -- Equivalent Water Thickness (cm)
      * ``cm`` -- Leaf Mass per unit area (g per cm^2)
      * ``psoil`` -- Soil moisture mix of the built-in soils: wet soil = 0, dry soil = 1.
        Ignored when ``soil_spectrum`` is given.
      * ``lai`` -- Leaf Area Index
      * ``hspot`` -- Hot spot parameter (leaf size / canopy height)
      * ``tts`` -- Solar zenith angle (degrees, 0 <= tts < 90)
      * ``tto`` -- Observer zenith angle (degrees, 0 <= tto < 90)
      * ``psi`` -- Relative azimuth between sun and sensor (degrees). 0 is the
        hotspot (sensor on the sun's side, looking away from it); 180 is the
        forward-scatter direction. Any value is wrapped onto [0, 180].
      * ``typelidf`` -- Type of leaf angle distribution to use (1 or 2)
      * ``lidfa`` -- Leaf distribution function parameter a (see below)
      * ``lidfb`` -- Leaf distribution function parameter b (see below)
      * ``soil_spectrum`` -- Optional soil reflectance, 2101 values for 400-2500 nm.

    If TypeLidf is 1 ``typelidf=1``:
        LIDFa and LIDFb define the average leaf slope and bimodality, with
        |LIDFa| + |LIDFb| <= 1. Predefined (LIDFa, LIDFb) tuples: Planophile,
        Erectophile, Plagiophile, Extremophile, Spherical, Uniform; unpack them,
        e.g. ``run_all(..., 1, *pyprosail.Spherical)``.

    If TypeLidf is 2 ``typelidf=2``:
        LIDFa is the average leaf angle (degrees) of an ellipsoidal distribution,
        0 is planophile and 90 is erectophile. LIDFb is ignored.
    """
    values = dict(n=n, cab=cab, car=car, cbrown=cbrown, cw=cw, cm=cm, lai=lai, hspot=hspot,
                  tts=tts, tto=tto, psi=psi, lidfa=lidfa, lidfb=lidfb)
    values = {name: float(value) for name, value in values.items()}
    _check_finite(**values)
    typelidf = int(typelidf)

    if soil_spectrum is None:
        psoil = float(psoil)
        _check_finite(psoil=psoil)
        use_soil = 0
        rsoil_in = np.zeros(_NW)
    else:
        rsoil_in = np.ascontiguousarray(soil_spectrum, dtype=np.float64)
        if rsoil_in.shape != (_NW,):
            raise ValueError(f"soil_spectrum must have shape ({_NW},) for 400-2500 nm, got {rsoil_in.shape}")
        if not np.all(np.isfinite(rsoil_in)) or rsoil_in.min() < 0 or rsoil_in.max() > 1:
            raise ValueError("soil_spectrum must be finite reflectance values in [0, 1]")
        psoil = None
        use_soil = 1

    _validate(values["n"], values["cab"], values["car"], values["cbrown"], values["cw"],
              values["cm"], psoil, values["lai"], values["hspot"], values["tts"],
              values["tto"], typelidf, values["lidfa"], values["lidfb"])
    if typelidf == 2:
        values["lidfb"] = 0.0

    resv, rsot, rdot, rsdt, rddt = run_fortran(
        values["n"], values["cab"], values["car"], values["cbrown"], values["cw"], values["cm"],
        0.0 if psoil is None else psoil, values["lai"], values["hspot"], values["tts"],
        values["tto"], wrap_psi(values["psi"]), typelidf, values["lidfa"], values["lidfb"],
        use_soil, rsoil_in,
    )
    return ProsailResult(WAVELENGTHS.copy(), resv, rsot, rdot, rsdt, rddt)


def run(
    n: float,
    cab: float,
    car: float,
    cbrown: float,
    cw: float,
    cm: float,
    psoil: float,
    lai: float,
    hspot: float,
    tts: float,
    tto: float,
    psi: float,
    typelidf: int,
    lidfa: int | float,
    lidfb: int | float,
) -> np.ndarray:
    """
    Runs the ProSAIL model and returns a (2101, 2) array of [wavelength_nm, resv].

    Same arguments as `run_all`. ``resv`` mixes the direct-sun BRF (``rsot``)
    and the diffuse-sky HDRF (``rdot``) with the sky-light fraction of
    Francois et al. (2002); it is not a pure bi-directional reflectance factor.
    Use `run_all` to get ``rsot`` and the other factors.
    """
    return run_all(n, cab, car, cbrown, cw, cm, psoil, lai, hspot, tts, tto, psi,
                   typelidf, lidfa, lidfb).as_array("resv")
