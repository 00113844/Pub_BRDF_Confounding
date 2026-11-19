"""PROSAIL simulation engine shared by BRDF.qmd, the Streamlit app and the cross-check scripts.

Two backends sit behind the same interface:

* ``"pyprosail"`` (default) -- the patched PyProSAIL Fortran code in vendor/pyprosail
  (PROSPECT-5B + 4SAIL, identical physics to the hsdar R package).
* ``"prosail_py"`` -- the pure-Python ``prosail`` package (jgomezdans), PROSPECT-5,
  installed with the ``dev`` dependency group. Used for cross-checks and as a fallback.

Geometry follows the project naming: ``sza`` (solar zenith), ``vza`` (view zenith) and
``raa`` (relative azimuth), all in degrees. ``raa = 0`` is the hotspot: the sensor sits
on the sun's side of the target and looks away from the sun (backscatter); ``raa = 180``
is forward scatter. Any raa is wrapped onto [0, 180] before it reaches 4SAIL, whose
volscatt routine assumes that range.

All spectra are on a 1 nm grid from 400 to 2500 nm, so ``index = wavelength - 400``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from functools import lru_cache
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from .indices import compute_index

WAVELENGTHS = np.arange(400, 2501)  # index = wavelength - 400

# 4SAIL divides by cos(zenith); keep angles clear of 90 degrees.
MAX_ZENITH = 85.0

FACTORS = ("resv", "rsot", "rdot", "rsdt", "rddt")
FACTOR_LABELS = {
    "resv": "Directional reflectance under sun + sky (HDRF-like, field conditions)",
    "rsot": "Bi-directional reflectance factor, direct sun only (BRF)",
    "rdot": "Hemispherical-directional reflectance factor, diffuse sky only",
    "rsdt": "Directional-hemispherical reflectance factor (black-sky albedo)",
    "rddt": "Bi-hemispherical reflectance factor (white-sky albedo)",
}

BACKENDS = ("pyprosail", "prosail_py")


@dataclass(frozen=True)
class CanopyParams:
    """PROSPECT-5B + 4SAIL inputs (units as in PROSAIL)."""

    N: float = 1.5          # Leaf structure parameter
    cab: float = 40.0       # Chlorophyll a+b (ug/cm2)
    car: float = 8.0        # Carotenoids (ug/cm2)
    cbrown: float = 0.0     # Brown pigment (arbitrary units)
    cw: float = 0.01        # Equivalent water thickness (cm)
    cm: float = 0.009       # Dry matter (g/cm2)
    lai: float = 2.5        # Leaf area index (m2/m2)
    typelidf: int = 2       # 1 = Verhoef two-parameter LIDF, 2 = Campbell ellipsoidal
    lidfa: float = 60.0     # typelidf 2: mean leaf angle (deg); typelidf 1: LIDF parameter a
    lidfb: float = 0.0      # typelidf 1: LIDF parameter b (bimodality); ignored for typelidf 2
    hspot: float = 0.01     # Hotspot parameter (leaf size / canopy height)
    psoil: float = 0.5      # Soil moisture mix of the built-in soils (0 = wet, 1 = dry)
    soil_scale: float = 1.0  # Soil brightness multiplier on the mixed soil spectrum

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "CanopyParams":
        """Build from a dict, ignoring keys that are not PROSAIL inputs and empty values."""
        names = {f.name: f.type for f in fields(cls)}
        kwargs = {}
        for key, value in values.items():
            if key not in names or value is None:
                continue
            if isinstance(value, float) and np.isnan(value):
                continue
            kwargs[key] = int(value) if key == "typelidf" else float(value)
        return cls(**kwargs)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    def updated(self, **changes) -> "CanopyParams":
        return replace(self, **changes)


def wrap_raa(raa):
    """Map relative azimuth (degrees, scalar or array) onto [0, 180]."""
    raa = np.asarray(raa, dtype=float)
    wrapped = np.abs(raa - 360.0 * np.round(raa / 360.0))
    return float(wrapped) if wrapped.ndim == 0 else wrapped


def _check_geometry(sza: float, vza: float) -> None:
    for name, value in (("sza", sza), ("vza", vza)):
        if not 0 <= value <= MAX_ZENITH:
            raise ValueError(f"{name} must be in [0, {MAX_ZENITH:g}] degrees, got {value}")


@lru_cache(maxsize=1)
def builtin_soils() -> tuple[np.ndarray, np.ndarray]:
    """Return the (dry, wet) soil spectra built into the PROSAIL Fortran code.

    With LAI = 0, 4SAIL returns the soil itself, so psoil = 1 gives Rsoil1 (dry)
    and psoil = 0 gives Rsoil2 (wet).
    """
    import pyprosail

    args = dict(n=1.5, cab=40, car=8, cbrown=0, cw=0.01, cm=0.009, lai=0.0, hspot=0.01,
                tts=30, tto=0, psi=0, typelidf=2, lidfa=45, lidfb=0)
    dry = pyprosail.run_all(psoil=1.0, **args).rsot
    wet = pyprosail.run_all(psoil=0.0, **args).rsot
    return dry, wet


def soil_spectrum(params: CanopyParams) -> np.ndarray:
    """Soil reflectance used by the pyprosail backend: soil_scale * (psoil*dry + (1-psoil)*wet)."""
    dry, wet = builtin_soils()
    return np.clip(params.soil_scale * (params.psoil * dry + (1 - params.psoil) * wet), 0.0, 1.0)


def skylight_fraction(sza: float) -> float:
    """Diffuse fraction of incoming light used by PROSAIL's resv (Francois et al., 2002)."""
    s = np.sin(np.radians(90.0 - sza))
    return 0.847 - 1.61 * s + 1.04 * s * s


def _simulate_pyprosail(p: CanopyParams, sza: float, vza: float, raa: float) -> dict[str, np.ndarray]:
    import pyprosail

    kwargs = dict(n=p.N, cab=p.cab, car=p.car, cbrown=p.cbrown, cw=p.cw, cm=p.cm,
                  psoil=p.psoil, lai=p.lai, hspot=p.hspot, tts=sza, tto=vza, psi=raa,
                  typelidf=p.typelidf, lidfa=p.lidfa, lidfb=p.lidfb)
    if p.soil_scale != 1.0:
        kwargs["soil_spectrum"] = soil_spectrum(p)
    res = pyprosail.run_all(**kwargs)
    return {factor: getattr(res, factor) for factor in FACTORS}


def _simulate_prosail_py(p: CanopyParams, sza: float, vza: float, raa: float) -> dict[str, np.ndarray]:
    try:
        import prosail
    except ImportError as exc:
        raise ImportError(
            "The 'prosail_py' backend needs the jgomezdans prosail package: uv sync --group dev"
        ) from exc

    rsot, rddt, rsdt, rdot = prosail.run_prosail(
        p.N, p.cab, p.car, p.cbrown, p.cw, p.cm, p.lai, p.lidfa, p.hspot,
        tts=sza, tto=vza, psi=raa, typelidf=p.typelidf, lidfb=p.lidfb,
        prospect_version="5", factor="ALL", rsoil=p.soil_scale, psoil=p.psoil,
    )
    # Same sun + sky weighting as the Fortran resv, with the package's Es/Ed spectra
    light = prosail.spectral_lib.light
    skyl = skylight_fraction(sza)
    direct, diffuse = (1 - skyl) * light.es, skyl * light.ed
    resv = (rdot * diffuse + rsot * direct) / (direct + diffuse)
    return {"resv": resv, "rsot": rsot, "rdot": rdot, "rsdt": rsdt, "rddt": rddt}


def simulate(
    params: CanopyParams,
    sza: float,
    vza: float,
    raa: float,
    backend: str = "pyprosail",
) -> dict[str, np.ndarray]:
    """Run PROSAIL once and return {factor: spectrum} plus ``"wavelength"``.

    ``raa`` may be any angle; it is wrapped onto [0, 180] (0 = hotspot).
    """
    _check_geometry(sza, vza)
    raa = wrap_raa(raa)
    if backend == "pyprosail":
        out = _simulate_pyprosail(params, sza, vza, raa)
    elif backend == "prosail_py":
        out = _simulate_prosail_py(params, sza, vza, raa)
    else:
        raise ValueError(f"backend must be one of {BACKENDS}, got {backend!r}")
    return {"wavelength": WAVELENGTHS.copy(), **{k: np.asarray(v, dtype=float) for k, v in out.items()}}


def brdf_grid(
    params: CanopyParams,
    sza: float,
    vza_values: Iterable[float],
    raa_values: Iterable[float],
    factor: str = "rsot",
    index: str | None = "NDVI",
    wavelength: int | None = None,
    backend: str = "pyprosail",
) -> pd.DataFrame:
    """Simulate a view-angle grid and return a tidy DataFrame (vza, raa, value).

    ``value`` is the vegetation ``index`` computed from ``factor``, or the reflectance
    at ``wavelength`` (nm) when ``index`` is None. raa keeps the caller's range
    (e.g. 0-360 for polar plots); each raa is wrapped onto [0, 180] for the model,
    so mirror-image azimuths are computed once.
    """
    if factor not in FACTORS:
        raise ValueError(f"factor must be one of {FACTORS}, got {factor!r}")
    if index is None and wavelength is None:
        raise ValueError("Give either an index name or a wavelength")

    vza_values = [float(v) for v in vza_values]
    raa_values = [float(r) for r in raa_values]
    cache: dict[tuple[float, float], float] = {}
    rows = []
    for vza in vza_values:
        for raa in raa_values:
            key = (vza, round(wrap_raa(raa), 9))
            if key not in cache:
                spectrum = simulate(params, sza, vza, raa, backend=backend)[factor]
                cache[key] = (compute_index(index, spectrum) if index is not None
                              else float(spectrum[int(wavelength) - 400]))
            rows.append({"vza": vza, "raa": raa, "value": cache[key]})
    return pd.DataFrame(rows)
