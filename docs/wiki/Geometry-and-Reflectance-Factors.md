# Geometry and Reflectance Factors

[← Home](Home.md)

## Angles

| Name | Engine name (Fortran name) | Range | Meaning |
|---|---|---|---|
| Solar zenith | `sza` (`tts`) | 0–85° | Angle of the sun from vertical |
| View zenith | `vza` (`tto`) | 0–85° (app: 0–80°) | Angle of the sensor's line of sight from vertical |
| Relative azimuth | `raa` (`psi`) | any; wrapped to 0–180° | Azimuth difference between sun and sensor |
| Solar azimuth | `saa` | 0–360° | Compass bearing of the sun, clockwise from North |
| View azimuth | `view_azimuth` | 0–360° | Compass bearing of the sensor *as seen from the target* |

### The relative azimuth convention

```
             sun                      sensor here: raa = 0°  (backscatter, hotspot side)
              \                      /
               \  sza               /  vza
                \                  /
   ──────────────●── target ──────────────
                                   sensor on the opposite side: raa = 180° (forward scatter)
```

- **`raa = 0°`:** the sensor stands on the same side as the sun and looks away from it, along the sun's rays. When `vza = sza` as well, the sensor sees no shadows: this is the **hotspot**, the brightest direction.
- **`raa = 180°`:** forward scatter. The sensor looks towards the sun and sees shaded leaf faces.
- **Other conventions differ.** Many satellite products and 6S define backscatter as 180°. Convert before comparing.
- **Converting from compass azimuths:** `solar.relative_azimuth(saa, view_azimuth)` returns `wrap(saa − view_azimuth)`.

### Why `raa` is wrapped

4SAIL's volume-scattering routine assumes 0 ≤ psi ≤ 180°, while its hotspot term only uses cos(psi). If you pass `raa = 350°`, the hotspot part treats it as 10° but the scattering part does not. Upstream PyProSAIL and the jgomezdans `prosail` package both have this problem. The size of the error:

- up to 25% at 670 nm;
- up to 14% at 800 nm for SZA 45°, VZA 60°;
- 15% at 800 nm for `raa = 360°`, which should equal `raa = 0°`.

The engine wraps every `raa` with `|raa − 360·round(raa/360)|`, so the two halves of a polar plot are mirror images, as physics requires for a horizontally uniform canopy.

### Why zenith angles are capped

4SAIL divides by cos(zenith), so 90° gives Inf/NaN. The wrapper rejects ≥ 90°, and the engine rejects > 85°. Results above about 75° are also where implementations start to disagree (see [Validation and Tests](Validation-and-Tests.md)).

## The five reflectance factors

| Name | Illumination | Viewing | What it is |
|---|---|---|---|
| `rsot` | Direct sun only | One direction | **BRF**: bi-directional reflectance factor. Contains the hotspot |
| `rdot` | Diffuse sky only (hemispherical) | One direction | Hemispherical-directional reflectance factor |
| `rsdt` | Direct sun | Hemispherical | Directional-hemispherical (black-sky albedo) |
| `rddt` | Diffuse sky | Hemispherical | Bi-hemispherical (white-sky albedo) |
| `resv` | Sun + sky | One direction | Weighted mix of `rsot` and `rdot`. What PyProSAIL and hsdar return by default |

`resv` is computed as:

```
skyl  = 0.847 − 1.61·sin(90° − sza) + 1.04·sin²(90° − sza)        (diffuse fraction, François et al. 2002)
resv  = (rdot·skyl·Ed + rsot·(1 − skyl)·Es) / (skyl·Ed + (1 − skyl)·Es)
```

Es and Ed are the direct and diffuse solar spectra stored in the model. Diffuse light is relatively stronger at short wavelengths, so `resv` is much less anisotropic than `rsot` in the blue and red. The table gives the hotspot-to-forward-scatter ratio in the principal plane for the ryegrass default canopy:

| SZA | 480 nm `rsot` | 480 nm `resv` | 800 nm `rsot` | 800 nm `resv` |
|---|---|---|---|---|
| 20° | 2.69 | 2.11 | 1.47 | 1.37 |
| 45° | 5.23 | 3.19 | 1.69 | 1.56 |
| 60° | 11.00 | 3.77 | 1.72 | 1.56 |

**Which factor to use:**

- **`rsot`** describes the canopy's intrinsic BRDF (physics, model comparisons).
- **`resv`** approximates what a field spectroradiometer records under a clear sky. A measured diffuse fraction is better where available.
- Always state the factor in captions and methods.

## Solar position – `solar.py`

| Function | Returns |
|---|---|
| `local_timezone(lat, lon)` | IANA time zone name (via `timezonefinder`); `"UTC"` over open ocean |
| `solar_position(lat, lon, when, tz=None)` | `SolarPosition(sza, saa, time_local, timezone)`. A naive `when` is taken as local time at that location |
| `daily_course(lat, lon, day, step_minutes=10)` | DataFrame of `time_local`, `sza`, `saa` through one local day |
| `relative_azimuth(saa, view_azimuth)` | PROSAIL `raa` in [0, 180] |

`sza` is pvlib's *apparent* (refraction-corrected) zenith, which is the direction light actually arrives from. Azimuths are compass bearings. Example: Perth, 21 December 2026, 12:30 local time gives SZA ≈ 9°, with the sun slightly north of zenith.

Next: [Streamlit App](Streamlit-App.md).
