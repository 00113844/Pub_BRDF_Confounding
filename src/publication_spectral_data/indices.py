"""Vegetation indices computed from 1 nm PROSAIL spectra (400-2500 nm, index = wavelength - 400).

Bands are single wavelengths, with no sensor spectral response applied.
"""

from __future__ import annotations

from typing import Callable, Mapping

import numpy as np

# Band centres (nm)
BLUE = 470
GREEN = 550
RED = 670
RED_EDGE_1 = 709
RED_EDGE_2 = 720
RED_EDGE_3 = 754
NIR = 800


INDEX_BANDS = (BLUE, GREEN, RED, 681, RED_EDGE_1, RED_EDGE_2, RED_EDGE_3, NIR)  # every band used below


def band(spectrum, wavelength: int) -> np.ndarray:
    """Reflectance at ``wavelength`` (nm).

    ``spectrum`` is a (2101,) or (..., 2101) array on the 400-2500 nm grid, or a mapping
    {wavelength: reflectance array} holding just the bands in ``INDEX_BANDS`` (as the
    geometry LUT stores them).
    """
    if isinstance(spectrum, Mapping):
        return np.asarray(spectrum[int(wavelength)])
    return np.asarray(spectrum)[..., int(wavelength) - 400]


def ndvi(s):
    nir, red = band(s, NIR), band(s, RED)
    return (nir - red) / (nir + red)


def evi(s):
    nir, red, blue = band(s, NIR), band(s, RED), band(s, BLUE)
    return 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)


def savi(s, soil_l: float = 0.5):
    nir, red = band(s, NIR), band(s, RED)
    return (1 + soil_l) * (nir - red) / (nir + red + soil_l)


def ndre(s):
    nir, red_edge = band(s, NIR), band(s, RED_EDGE_2)
    return (nir - red_edge) / (nir + red_edge)


def gndvi(s):
    nir, green = band(s, NIR), band(s, GREEN)
    return (nir - green) / (nir + green)


def mtci(s):
    # MERIS terrestrial chlorophyll index (Dash & Curran, 2004): bands 754, 709, 681 nm
    r754, r709, r681 = band(s, RED_EDGE_3), band(s, RED_EDGE_1), band(s, 681)
    return (r754 - r709) / (r709 - r681)


INDICES: dict[str, Callable] = {
    "NDVI": ndvi,
    "EVI": evi,
    "SAVI": savi,
    "NDRE": ndre,
    "GNDVI": gndvi,
    "MTCI": mtci,
}

INDEX_FORMULAS = {
    "NDVI": "(R800 - R670) / (R800 + R670)",
    "EVI": "2.5 (R800 - R670) / (R800 + 6 R670 - 7.5 R470 + 1)",
    "SAVI": "1.5 (R800 - R670) / (R800 + R670 + 0.5)",
    "NDRE": "(R800 - R720) / (R800 + R720)",
    "GNDVI": "(R800 - R550) / (R800 + R550)",
    "MTCI": "(R754 - R709) / (R709 - R681)",
}


def compute_index(name: str, spectrum: np.ndarray):
    """Compute index ``name`` (see INDICES) from a spectrum or stack of spectra."""
    try:
        func = INDICES[name.upper()]
    except KeyError:
        raise ValueError(f"Unknown index {name!r}; choose from {list(INDICES)}") from None
    value = func(spectrum)
    return float(value) if np.ndim(value) == 0 else value
