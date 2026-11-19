"""Crop growth-stage parameter database (data/crop_parameters/growth_stages.csv).

One row per crop and Zadoks stage. Blank cells mean no sourced value was found;
they fall back to the CanopyParams defaults and are reported as such.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .prosail_engine import CanopyParams

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "crop_parameters" / "growth_stages.csv"

REQUIRED_COLUMNS = ["crop", "zadoks", "stage_name", "lai_min", "lai_typ", "lai_max"]
PROSAIL_COLUMNS = ["N", "cab", "car", "cbrown", "cw", "cm", "typelidf", "lidfa", "lidfb",
                   "hspot", "psoil"]
LAI_LEVELS = ("lai_min", "lai_typ", "lai_max")


def load_growth_stages(path: Path | str = DATA_FILE) -> pd.DataFrame:
    """Read and check the growth-stage table, sorted by crop and Zadoks code."""
    table = pd.read_csv(path, comment="#")
    missing = [c for c in REQUIRED_COLUMNS if c not in table.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    table["zadoks"] = table["zadoks"].astype(int)
    for col in LAI_LEVELS + tuple(c for c in PROSAIL_COLUMNS if c in table.columns):
        table[col] = pd.to_numeric(table[col], errors="coerce")
    lai = table[list(LAI_LEVELS)]
    bad = table[(lai["lai_min"] > lai["lai_typ"]) | (lai["lai_typ"] > lai["lai_max"])]
    if not bad.empty:
        raise ValueError(f"lai_min <= lai_typ <= lai_max violated for Zadoks {bad['zadoks'].tolist()}")
    return table.sort_values(["crop", "zadoks"]).reset_index(drop=True)


def stage_params(row: pd.Series, lai_level: str = "lai_typ",
                 defaults: CanopyParams = CanopyParams()) -> tuple[CanopyParams, list[str]]:
    """PROSAIL parameters for one table row, plus the names of inputs taken from ``defaults``."""
    if lai_level not in LAI_LEVELS:
        raise ValueError(f"lai_level must be one of {LAI_LEVELS}")
    values = {col: row.get(col) for col in PROSAIL_COLUMNS}
    values["lai"] = row.get(lai_level)
    present = {k: v for k, v in values.items() if v is not None and not pd.isna(v)}
    defaulted = sorted(set(values) - set(present))
    params = defaults.updated(**{k: int(v) if k == "typelidf" else float(v) for k, v in present.items()})
    return params, defaulted
