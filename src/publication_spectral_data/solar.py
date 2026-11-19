"""Solar geometry from location and local time (pvlib), converted to PROSAIL angles.

Azimuths are compass angles: degrees clockwise from true North. ``view_azimuth``
is the azimuth of the sensor's position as seen from the target, so a sensor
standing on the sun's side (view_azimuth = solar azimuth) observes the hotspot
(raa = 0).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pvlib

from .prosail_engine import wrap_raa


@dataclass(frozen=True)
class SolarPosition:
    sza: float        # apparent solar zenith angle (deg), refraction-corrected
    saa: float        # solar azimuth (deg clockwise from North)
    time_local: pd.Timestamp
    timezone: str

    @property
    def above_horizon(self) -> bool:
        return self.sza < 90.0


@lru_cache(maxsize=1)
def _tz_finder():
    from timezonefinder import TimezoneFinder

    return TimezoneFinder()


def local_timezone(lat: float, lon: float) -> str:
    """IANA time zone name at (lat, lon); falls back to UTC over open ocean."""
    return _tz_finder().timezone_at(lat=lat, lng=lon) or "UTC"


def _localize(lat: float, lon: float, when: datetime, tz: str | None) -> pd.Timestamp:
    tz = tz or local_timezone(lat, lon)
    ts = pd.Timestamp(when)
    return ts.tz_localize(ZoneInfo(tz)) if ts.tzinfo is None else ts


def solar_position(lat: float, lon: float, when: datetime, tz: str | None = None) -> SolarPosition:
    """Sun position at ``when``; naive datetimes are local time at (lat, lon)."""
    ts = _localize(lat, lon, when, tz)
    pos = pvlib.solarposition.get_solarposition(pd.DatetimeIndex([ts]), lat, lon)
    return SolarPosition(
        sza=float(pos["apparent_zenith"].iloc[0]),
        saa=float(pos["azimuth"].iloc[0]),
        time_local=ts,
        timezone=str(ts.tzinfo),
    )


def daily_course(lat: float, lon: float, day: date, step_minutes: int = 10,
                 tz: str | None = None) -> pd.DataFrame:
    """Solar zenith and azimuth through one local day (columns: time_local, sza, saa)."""
    tz = tz or local_timezone(lat, lon)
    start = pd.Timestamp(datetime.combine(day, time(0, 0)), tz=ZoneInfo(tz))
    times = pd.date_range(start, start + pd.Timedelta(days=1), freq=f"{step_minutes}min",
                          inclusive="left")
    pos = pvlib.solarposition.get_solarposition(times, lat, lon)
    return pd.DataFrame({
        "time_local": times,
        "sza": pos["apparent_zenith"].to_numpy(),
        "saa": pos["azimuth"].to_numpy(),
    })


def relative_azimuth(saa, view_azimuth):
    """PROSAIL relative azimuth in [0, 180] (0 = hotspot) from compass azimuths."""
    return wrap_raa(np.asarray(saa, dtype=float) - np.asarray(view_azimuth, dtype=float))
