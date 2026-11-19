"""Geometry look-up tables: PROSAIL reflectance on a (sza, vza, raa) grid for one canopy.

Continental scenarios need hundreds of thousands of geometries per canopy. A LUT runs PROSAIL
once per grid node (through :func:`prosail_engine.simulate`, so azimuth wrapping and angle
limits are the shared ones) and keeps only the bands the vegetation indices need
(:data:`indices.INDEX_BANDS`). Queries use trilinear interpolation.

The relative-azimuth grid is denser near the hotspot (raa = 0). Even so, interpolation
smooths the hotspot peak where vza is close to sza and raa is close to 0. Use
:func:`prosail_engine.simulate` directly for those geometries when the peak value matters.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .indices import INDEX_BANDS, compute_index
from .prosail_engine import FACTORS, CanopyParams, simulate

LUT_DIR = Path(__file__).resolve().parents[2] / "results" / "lut"

DEFAULT_SZA = np.arange(0.0, 81.0, 2.0)
DEFAULT_VZA = np.arange(0.0, 41.0, 2.0)
DEFAULT_RAA = np.array([0, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90,
                        100, 110, 120, 130, 140, 150, 160, 170, 180], dtype=float)


@dataclass
class GeometryLUT:
    params: CanopyParams
    sza: np.ndarray
    vza: np.ndarray
    raa: np.ndarray
    bands: tuple[int, ...]
    factors: tuple[str, ...]
    values: np.ndarray            # (n_sza, n_vza, n_raa, n_factors, n_bands)
    _interp: RegularGridInterpolator | None = field(default=None, repr=False)

    def _interpolator(self) -> RegularGridInterpolator:
        if self._interp is None:
            flat = self.values.reshape(*self.values.shape[:3], -1)
            self._interp = RegularGridInterpolator((self.sza, self.vza, self.raa), flat,
                                                   bounds_error=False, fill_value=None)
        return self._interp

    def bands_at(self, sza, vza, raa, factor: str = "rsot") -> dict[int, np.ndarray]:
        """{wavelength: reflectance} at the given geometries (arrays broadcast together).

        ``raa`` may be any angle (wrapped onto [0, 180]); points outside the grid raise.
        """
        sza, vza, raa = np.broadcast_arrays(*(np.asarray(a, dtype=float) for a in (sza, vza, raa)))
        raa = np.abs(raa - 360.0 * np.round(raa / 360.0))
        for name, a, grid in (("sza", sza, self.sza), ("vza", vza, self.vza)):
            if a.size and (a.min() < grid[0] - 1e-9 or a.max() > grid[-1] + 1e-9):
                raise ValueError(f"{name} outside LUT range [{grid[0]}, {grid[-1]}]")
        pts = np.stack([sza.ravel(), vza.ravel(), raa.ravel()], axis=-1)
        out = self._interpolator()(pts).reshape(*sza.shape, len(self.factors), len(self.bands))
        f = self.factors.index(factor)
        return {wl: out[..., f, i] for i, wl in enumerate(self.bands)}

    def index_at(self, name: str, sza, vza, raa, factor: str = "rsot") -> np.ndarray:
        """Vegetation index ``name`` at the given geometries."""
        return np.asarray(compute_index(name, self.bands_at(sza, vza, raa, factor)))

    def save(self, path: Path | str) -> None:
        np.savez_compressed(path, params=json.dumps(self.params.to_dict()), sza=self.sza,
                            vza=self.vza, raa=self.raa, bands=np.array(self.bands),
                            factors=np.array(self.factors), values=self.values)

    @classmethod
    def load(cls, path: Path | str) -> "GeometryLUT":
        z = np.load(path, allow_pickle=False)
        return cls(params=CanopyParams.from_mapping(json.loads(str(z["params"]))),
                   sza=z["sza"], vza=z["vza"], raa=z["raa"],
                   bands=tuple(int(b) for b in z["bands"]),
                   factors=tuple(str(f) for f in z["factors"]), values=z["values"])


def _node(args):
    params, sza, vza, raa, factors, idx = args
    spectra = simulate(params, sza, vza, raa)
    return np.array([[spectra[f][wl - 400] for wl in INDEX_BANDS] for f in factors])


def build_lut(params: CanopyParams,
              sza: Sequence[float] = DEFAULT_SZA,
              vza: Sequence[float] = DEFAULT_VZA,
              raa: Sequence[float] = DEFAULT_RAA,
              factors: Sequence[str] = ("rsot", "resv"),
              processes: int = 1) -> GeometryLUT:
    """Run PROSAIL on every grid node.

    ``processes > 1`` uses a process pool (the Fortran keeps module state, so threads are not
    safe). On Windows, call it from under ``if __name__ == "__main__":``.
    """
    sza, vza, raa = (np.asarray(a, dtype=float) for a in (sza, vza, raa))
    factors = tuple(factors)
    bad = [f for f in factors if f not in FACTORS]
    if bad:
        raise ValueError(f"Unknown factors {bad}; choose from {FACTORS}")
    jobs = []
    for i, s in enumerate(sza):
        for j, v in enumerate(vza):
            # At nadir the azimuth does not matter: run once and copy across raa.
            raas = raa[:1] if v == 0 else raa
            for k, r in enumerate(raas):
                jobs.append((params, s, v, r, factors, (i, j, k)))
    if processes > 1:
        from multiprocessing import Pool
        with Pool(processes) as pool:
            results = pool.map(_node, jobs, chunksize=64)
    else:
        results = [_node(job) for job in jobs]

    values = np.empty((len(sza), len(vza), len(raa), len(factors), len(INDEX_BANDS)))
    for job, res in zip(jobs, results):
        i, j, k = job[-1]
        if vza[j] == 0:
            values[i, j, :] = res
        else:
            values[i, j, k] = res
    return GeometryLUT(params=params, sza=sza, vza=vza, raa=raa, bands=INDEX_BANDS,
                       factors=factors, values=values)


def lut_key(params: CanopyParams, sza, vza, raa, factors) -> str:
    payload = json.dumps({"params": params.to_dict(), "sza": list(map(float, sza)),
                          "vza": list(map(float, vza)), "raa": list(map(float, raa)),
                          "factors": list(factors), "bands": list(INDEX_BANDS)}, sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


def cached_lut(params: CanopyParams,
               sza: Sequence[float] = DEFAULT_SZA,
               vza: Sequence[float] = DEFAULT_VZA,
               raa: Sequence[float] = DEFAULT_RAA,
               factors: Sequence[str] = ("rsot", "resv"),
               processes: int = 1,
               directory: Path | str = LUT_DIR) -> GeometryLUT:
    """:func:`build_lut`, cached on disk under ``results/lut`` by a hash of all inputs."""
    directory = Path(directory)
    path = directory / f"lut_{lut_key(params, sza, vza, raa, factors)}.npz"
    if path.exists():
        return GeometryLUT.load(path)
    lut = build_lut(params, sza, vza, raa, factors, processes)
    directory.mkdir(parents=True, exist_ok=True)
    lut.save(path)
    return lut
