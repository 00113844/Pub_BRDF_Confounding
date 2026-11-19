"""Checks on the Australian sun-view geometry scenarios."""

from datetime import date, datetime, time

import numpy as np
import pandas as pd
import pytest

from publication_spectral_data.geometry_scenarios import (
    S2_HALF_SWATH_KM,
    handheld_geometry,
    load_sites,
    sentinel2_geometry,
    sentinel2_heading,
    sentinel2_overpass_utc,
    sentinel2_view,
    uav_geometry,
)
from publication_spectral_data.solar import solar_position


@pytest.fixture(scope="module")
def sites():
    return load_sites()


def _site(sites, name):
    return sites[sites["site"] == name]


def test_sites_have_australian_time_zones(sites):
    assert sites["tz"].str.startswith("Australia/").all()
    assert sites["lat"].between(-44, -10).all() and sites["lon"].between(112, 154).all()


def test_handheld_matches_solar_position(sites):
    g = handheld_geometry(_site(sites, "Wagga Wagga"), [date(2026, 7, 15)], [time(11, 0)])
    ref = solar_position(-35.12, 147.37, datetime(2026, 7, 15, 11, 0))
    assert g["sza"].iloc[0] == pytest.approx(ref.sza, abs=1e-6)
    assert g["vza"].iloc[0] == 0 and g["raa"].iloc[0] == 0


def test_dst_shifts_clock_time_in_nsw_not_qld(sites):
    # In January, 12:00 clock time is 11:00 standard time in NSW (DST) but 12:00 in QLD.
    g = handheld_geometry(sites[sites["site"].isin(["Wagga Wagga", "Gatton"])],
                          [date(2026, 1, 15)], [time(12, 0)])
    dst = dict(zip(g["site"], g["dst"]))
    assert dst["Wagga Wagga"] and not dst["Gatton"]
    wagga = g[g["site"] == "Wagga Wagga"]["time_local"].iloc[0]
    assert wagga.utcoffset() == pd.Timedelta(hours=11)
    std = solar_position(-35.12, 147.37, datetime(2026, 1, 15, 11, 0), tz="Etc/GMT-10")
    assert g[g["site"] == "Wagga Wagga"]["sza"].iloc[0] == pytest.approx(std.sza, abs=1e-6)


def test_perth_has_no_dst(sites):
    g = handheld_geometry(sites[sites["tz"] == "Australia/Perth"], [date(2026, 1, 15)], [time(12, 0)])
    assert not g["dst"].any()


def test_sentinel2_overpass_is_mid_morning_solar_time():
    utc = sentinel2_overpass_utc(date(2026, 3, 20), lon=150.0)
    assert utc == pd.Timestamp("2026-03-20 00:30:00", tz="UTC")


def test_sentinel2_overpass_sun_matches_solar_position(sites):
    loc = _site(sites, "Northam")
    g = sentinel2_geometry(loc, [date(2026, 6, 15)], across_track_km=[0.0])
    utc = sentinel2_overpass_utc(date(2026, 6, 15), loc["lon"].iloc[0])
    ref = solar_position(loc["lat"].iloc[0], loc["lon"].iloc[0], utc.to_pydatetime())
    assert g["sza"].iloc[0] == pytest.approx(ref.sza, abs=1e-6)


def test_sentinel2_view_geometry():
    assert sentinel2_view(0.0, -30)[0] == 0.0
    vza_edge, vaa_right = sentinel2_view(S2_HALF_SWATH_KM, -30)
    assert 11.0 < vza_edge < 12.5          # swath edge of Sentinel-2 MSI is ~11-12 deg at ground
    _, vaa_left = sentinel2_view(-S2_HALF_SWATH_KM, -30)
    assert (vaa_left - vaa_right) % 360 == pytest.approx(180.0)
    assert 180 < sentinel2_heading(-30) < 200   # descending pass heads SSW


def test_raa_in_range_for_all_sensors(sites):
    days = [date(2026, 1, 15), date(2026, 7, 15)]
    for g in (handheld_geometry(sites, days, [time(9, 0), time(15, 0)]),
              sentinel2_geometry(sites, days),
              uav_geometry(sites.head(3), days, time(11, 0))):
        assert len(g) > 0
        assert g["raa"].between(0, 180).all()
        assert (g["sza"] <= 80).all()
