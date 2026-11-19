# Troubleshooting

[← Home](Home.md)

## Building `pyprosail`

| Symptom | Cause | Fix |
|---|---|---|
| `uv sync` fails at `meson setup`, with no Fortran compiler found | gfortran is not on `PATH` | Add `<msys64>\ucrt64\bin` to `PATH` and retry (see [Getting Started](Getting-Started.md#1-fortran-toolchain-one-off)) |
| Meson picks MSVC, or fails to link | gcc is not on `PATH`, so the Visual Studio toolchain is found instead | Make sure `gcc` comes from `ucrt64\bin`: `where gcc` |
| `Readme file not found` | `vendor/pyprosail/README.md` is missing | Restore it; meson-python requires it |
| Fortran edits have no effect | uv cached the built wheel | `uv sync --reinstall-package pyprosail` |
| `ImportError: DLL load failed` on `import pyprosail` | A build without static linking | Check that `meson.build` has the Windows `-static` link arguments, then rebuild |
| MSYS2 installer exits with code 1 | No admin rights | Use the portable `msys2-base-*.sfx.exe` archive |

## Python environment

| Symptom | Fix |
|---|---|
| `No Python at '...cpython-3.11...'` | The base interpreter was removed. Run `uv python install 3.12` then `uv venv --clear --python 3.12`, then `uv sync` |
| `ImportError: ... 'prosail_py' backend needs ...` | Install the dev group: `uv sync` (the default) or `uv sync --group dev` |
| Quarto uses the wrong Python | Re-register the `hyperspectral-brdf` kernel; check that the qmd header says `jupyter: hyperspectral-brdf` |
| `quarto: command not found` | Install Quarto from https://quarto.org |

## Model errors

| Error | Meaning |
|---|---|
| `sza must be in [0, 85] degrees` | Sun too low. For a real date and time, check the sun is up |
| `If typelidf is 1, abs(lidfa) + abs(lidfb) must not be greater than 1` | That LIDF pair gives negative leaf-angle weights. Choose a valid pair or use `typelidf=2` |
| `If typelidf is 2, lidfa is the mean leaf angle in [0, 90]` | You passed Verhoef parameters with type 2 |
| `psoil must be in [0, 1]` | Use `soil_scale` for brightness, not psoil |
| A polar plot is not mirror-symmetric | You called a PROSAIL package directly with raw 0–360° azimuths. Go through `prosail_engine` |

## Streamlit app

| Symptom | Fix |
|---|---|
| *Growth-stage table not found*, even though the file exists | The app cached the result from before the file existed. Use menu → *Clear cache*, or restart |
| The map click doesn't move the marker | Click once and wait for the rerun; very fast repeated clicks can be dropped |
| A stage spectrum is missing from the "across stages" plot | That stage has no sourced typical LAI. This is intended; see [Growth-Stage Database](Growth-Stage-Database.md#known-gaps-and-caveats) |
| The app is visible on the network | Start it with `--server.address localhost` |
| Slow polar plot | Use a 10° or 15° angle step. Results are cached, so returning to an earlier setting is instant |

## R

| Symptom | Fix |
|---|---|
| `renv::install("gitlab::jbferet/prosail")` is slow | It installs about 95 dependencies (around 5 minutes); `prosail` itself is built from source |
| `The project is out-of-sync` | `renv::status()`, then `renv::snapshot()` after an intentional change |
| `hsdar` will not install | It is archived and needs the retired `rgdal`. It isn't needed: its Fortran is identical to `vendor/pyprosail` |
| VS Code terminal finds the wrong R | `.vscode/settings.json` should point to `R-4.6.1\bin` |

[← Home](Home.md)
