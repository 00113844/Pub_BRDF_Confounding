"""Sun-view geometry scenarios across Australia for three sensor types.

Every builder returns a tidy DataFrame with one row per (location, time, view) and the columns
``site, state, lat, lon, time_local, tz, dst, sza, saa, vza, vaa, raa`` (degrees; azimuths are
compass angles clockwise from North; ``vaa`` is the azimuth of the sensor as seen from the
target, so ``raa = 0`` is the hotspot). Rows with the sun below ``max_sza`` only are kept.

Sensors:

* **Handheld** -- nadir view at fixed local *clock* times, so time zones and daylight saving
  shift the solar geometry exactly as they shift a field protocol such as "measure 10:00-14:00".
* **Sentinel-2** -- one overpass at ~10:30 local mean solar time (descending node), with the
  view zenith/azimuth of a target at a given across-track distance from the ground track.
  The orbit model is a simple spherical approximation (see :func:`sentinel2_view`).
* **UAV** -- one flight time, with a set of view zenith/azimuth pairs inside the camera field
  of view (or from deliberate oblique shots).
"""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pvlib

from .prosail_engine import MAX_ZENITH
from .solar import local_timezone, relative_azimuth

SITES_FILE = Path(__file__).resolve().parents[2] / "data" / "sites" / "australia_sites.csv"

# Reference geometry for "geometry-free" values: nadir view, SZA 45 deg (as in MODIS NBAR).
REFERENCE_GEOMETRY = {"sza": 45.0, "vza": 0.0, "raa": 0.0}

# Sentinel-2 orbit (ESA Sentinel-2 User Handbook): 786 km mean altitude, 98.62 deg inclination,
# 10:30 mean local solar time at the descending node, 290 km swath.
S2_ALTITUDE_KM = 786.0
S2_INCLINATION_DEG = 98.62
S2_LMST_HOURS = 10.5
S2_HALF_SWATH_KM = 145.0
EARTH_RADIUS_KM = 6371.0

# Mainland Australia bounding box used for the regular grid.
AUS_BOUNDS = {"lat_min": -44.0, "lat_max": -10.0, "lon_min": 112.5, "lon_max": 154.0}

COLUMNS = ["site", "state", "lat", "lon", "time_local", "tz", "dst",
           "sza", "saa", "vza", "vaa", "raa"]


# --------------------------------------------------------------------------- locations

def load_sites(path: Path | str = SITES_FILE) -> pd.DataFrame:
    """Named sites with their IANA time zone added (column ``tz``)."""
    sites = pd.read_csv(path, comment="#")
    sites["tz"] = [local_timezone(la, lo) for la, lo in zip(sites["lat"], sites["lon"])]
    return sites


def australia_grid(step: float = 0.5, land_only: bool = True) -> pd.DataFrame:
    """Regular lat/lon grid (cell centres) over Australia, with time zones.

    ``land_only`` keeps cells whose centre falls on land in the Natural Earth 1:50m land
    polygons (cartopy downloads them on first use). Cells over the sea get ``tz = UTC`` from
    timezonefinder and are dropped anyway.
    """
    b = AUS_BOUNDS
    lats = np.arange(b["lat_min"] + step / 2, b["lat_max"], step)
    lons = np.arange(b["lon_min"] + step / 2, b["lon_max"], step)
    lon2, lat2 = np.meshgrid(lons, lats)
    grid = pd.DataFrame({"lat": lat2.ravel().round(4), "lon": lon2.ravel().round(4)})
    if land_only:
        grid = grid[_on_land(grid["lat"].to_numpy(), grid["lon"].to_numpy())]
    grid["tz"] = [local_timezone(la, lo) for la, lo in zip(grid["lat"], grid["lon"])]
    grid = grid[grid["tz"].str.startswith("Australia/")]
    grid.insert(0, "site", [f"grid_{la:.2f}_{lo:.2f}" for la, lo in zip(grid["lat"], grid["lon"])])
    grid.insert(1, "state", "")
    return grid.reset_index(drop=True)


def _on_land(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    import cartopy.io.shapereader as shpreader
    import shapely
    from shapely.ops import unary_union

    reader = shpreader.Reader(shpreader.natural_earth("50m", "physical", "land"))
    land = unary_union([g for g in reader.geometries()
                        if g.intersects(shapely.box(110, -45, 155, -9))])
    land = land.intersection(shapely.box(110, -45, 155, -9))
    return shapely.contains_xy(land, lon, lat)


# --------------------------------------------------------------------------- sun position

def _sun(lat: float, lon: float, times: pd.DatetimeIndex) -> pd.DataFrame:
    pos = pvlib.solarposition.get_solarposition(times, lat, lon)
    return pd.DataFrame({"sza": pos["apparent_zenith"].to_numpy(),
                         "saa": pos["azimuth"].to_numpy()})


def _local_times(day: date, clock: time, tz: str) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, clock), tz=ZoneInfo(tz))


def _finish(rows: list[pd.DataFrame], max_sza: float) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    out = pd.concat(rows, ignore_index=True)
    out["raa"] = relative_azimuth(out["saa"].to_numpy(), out["vaa"].to_numpy())
    out = out[(out["sza"] <= max_sza) & (out["vza"] <= MAX_ZENITH)]
    return out[COLUMNS + [c for c in out.columns if c not in COLUMNS]].reset_index(drop=True)


def _location_rows(locations: pd.DataFrame):
    for loc in locations.itertuples(index=False):
        tz = getattr(loc, "tz", None) or local_timezone(loc.lat, loc.lon)
        yield loc, tz


# --------------------------------------------------------------------------- handheld

def handheld_geometry(locations: pd.DataFrame, dates: Iterable[date],
                      clock_times: Sequence[time], max_sza: float = 80.0) -> pd.DataFrame:
    """Nadir view at fixed local clock times (DST applied where the state observes it).

    At nadir the relative azimuth has no effect; ``vaa`` is set equal to the solar azimuth so
    that ``raa = 0``.
    """
    rows = []
    dates = list(dates)
    for loc, tz in _location_rows(locations):
        stamps = [_local_times(d, t, tz) for d in dates for t in clock_times]
        idx = pd.DatetimeIndex(stamps)
        sun = _sun(loc.lat, loc.lon, idx)
        rows.append(pd.DataFrame({
            "site": loc.site, "state": loc.state, "lat": loc.lat, "lon": loc.lon,
            "time_local": stamps, "tz": tz,
            "dst": [bool(s.dst()) for s in stamps],
            "sza": sun["sza"], "saa": sun["saa"], "vza": 0.0, "vaa": sun["saa"],
            "clock_time": [s.strftime("%H:%M") for s in stamps],
        }))
    return _finish(rows, max_sza)


# --------------------------------------------------------------------------- Sentinel-2

def sentinel2_overpass_utc(day: date, lon: float, lmst_hours: float = S2_LMST_HOURS) -> pd.Timestamp:
    """UTC time at which local *mean* solar time at ``lon`` equals ``lmst_hours``.

    Approximation: the descending node crosses the equator at 10:30 LMST, and over southern
    Australia the local time at overpass is within a few minutes of that.
    """
    hours = lmst_hours - lon / 15.0
    return (pd.Timestamp(datetime.combine(day, time(0, 0)), tz="UTC")
            + pd.Timedelta(hours=hours)).round("s")


def sentinel2_heading(lat: float, inclination: float = S2_INCLINATION_DEG) -> float:
    """Compass heading of the descending ground track at ``lat`` (no Earth-rotation term).

    On a sphere, cos(i) = cos(lat) sin(A) along the orbit; the descending branch of a
    retrograde (i > 90 deg) orbit heads south-south-west, so A = 180 + asin(-cos i / cos lat).
    """
    s = np.clip(-np.cos(np.radians(inclination)) / np.cos(np.radians(lat)), -1, 1)
    return float((180.0 + np.degrees(np.arcsin(s))) % 360.0)


def sentinel2_view(across_track_km: float, lat: float) -> tuple[float, float]:
    """View zenith and view azimuth for a target ``across_track_km`` from the ground track.

    Positive distances are to the right of the direction of travel (west-north-west on the
    descending pass), so those targets see the satellite to their east-south-east.
    VZA uses spherical geometry: the off-nadir angle at the satellite is converted to the
    zenith angle at the ground.
    """
    x = float(across_track_km)
    if x == 0:
        return 0.0, sentinel2_heading(lat) - 90.0
    central = abs(x) / EARTH_RADIUS_KM                       # Earth-central angle (rad)
    r, rs = EARTH_RADIUS_KM, EARTH_RADIUS_KM + S2_ALTITUDE_KM
    slant = np.sqrt(r**2 + rs**2 - 2 * r * rs * np.cos(central))
    off_nadir = np.arcsin(r * np.sin(central) / slant)
    vza = float(np.degrees(off_nadir + central))
    heading = sentinel2_heading(lat)
    vaa = (heading - 90.0) if x > 0 else (heading + 90.0)
    return vza, float(vaa % 360.0)


def sentinel2_geometry(locations: pd.DataFrame, dates: Iterable[date],
                       across_track_km: Sequence[float] = (-S2_HALF_SWATH_KM, 0.0, S2_HALF_SWATH_KM),
                       max_sza: float = 80.0) -> pd.DataFrame:
    """Geometry of a Sentinel-2 overpass for each location, date and across-track position."""
    rows = []
    dates = list(dates)
    for loc, tz in _location_rows(locations):
        utc = pd.DatetimeIndex([sentinel2_overpass_utc(d, loc.lon) for d in dates])
        local = utc.tz_convert(ZoneInfo(tz))
        sun = _sun(loc.lat, loc.lon, utc)
        for x in across_track_km:
            vza, vaa = sentinel2_view(x, loc.lat)
            rows.append(pd.DataFrame({
                "site": loc.site, "state": loc.state, "lat": loc.lat, "lon": loc.lon,
                "time_local": list(local), "tz": tz,
                "dst": [bool(s.dst()) for s in local],
                "sza": sun["sza"], "saa": sun["saa"], "vza": vza, "vaa": vaa,
                "across_track_km": float(x),
            }))
    return _finish(rows, max_sza)


# --------------------------------------------------------------------------- UAV

def uav_view_grid(max_vza: float = 35.0, vza_step: float = 5.0,
                  vaa_step: float = 30.0) -> list[tuple[float, float]]:
    """(vza, vaa) pairs covering a camera field of view, nadir included once."""
    views = [(0.0, 0.0)]
    for vza in np.arange(vza_step, max_vza + 1e-9, vza_step):
        for vaa in np.arange(0.0, 360.0, vaa_step):
            views.append((float(vza), float(vaa)))
    return views


def uav_geometry(locations: pd.DataFrame, dates: Iterable[date], clock_time: time,
                 views: Sequence[tuple[float, float]] | None = None,
                 max_sza: float = 80.0) -> pd.DataFrame:
    """Geometry of every view in ``views`` (default :func:`uav_view_grid`) at one clock time."""
    views = list(views) if views is not None else uav_view_grid()
    hh = handheld_geometry(locations, dates, [clock_time], max_sza=max_sza)
    rows = []
    for vza, vaa in views:
        part = hh.drop(columns="raa").copy()
        part["vza"], part["vaa"] = vza, vaa
        rows.append(part)
    return _finish(rows, max_sza)


def monthly_dates(year: int = 2026, day: int = 15) -> list[date]:
    """The ``day``-th of every month of ``year``."""
    return [date(year, m, day) for m in range(1, 13)]
