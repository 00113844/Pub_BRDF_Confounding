# Getting Started

[← Home](Home.md)

## Requirements

| Tool | Why | Version used |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | Python environment and dependencies | – |
| Python | Analysis code, app | 3.12 |
| gfortran + gcc | Compiling the PROSAIL Fortran during `uv sync` | GCC 16.2 (MSYS2 UCRT64) |
| R + renv | R `prosail` cross-check | R 4.6.1 |
| Quarto | Rendering `BRDF.qmd` and `article.qmd` | not installed yet on the dev machine |

## 1. Fortran toolchain (one-off)

The PROSAIL engine is compiled from Fortran when the Python environment is built.

**Windows (no admin rights needed):**

1. From the [MSYS2 releases](https://github.com/msys2/msys2-installer/releases), download `msys2-base-x86_64-<date>.sfx.exe`. Check its SHA-256 against the digest on the release page.
2. Unpack it into your user folder:
   ```powershell
   .\msys2-base-x86_64-<date>.sfx.exe -y "-o$env:LOCALAPPDATA\Programs"
   ```
3. Install the compilers:
   ```powershell
   $bash = "$env:LOCALAPPDATA\Programs\msys64\usr\bin\bash.exe"
   & $bash -lc "pacman -Syu --noconfirm"
   & $bash -lc "pacman -S --noconfirm --needed mingw-w64-ucrt-x86_64-gcc-fortran mingw-w64-ucrt-x86_64-gcc"
   ```
4. Put `%LOCALAPPDATA%\Programs\msys64\ucrt64\bin` on `PATH` when running `uv sync`. The VS Code terminal does this through `.vscode/settings.json`.

With admin rights, you can use the normal MSYS2 installer (`C:\msys64`) instead.

**Linux:** `sudo apt install gfortran gcc`. **macOS:** `brew install gcc`.

The extension links the gfortran runtime statically on Windows. Once built, it runs without MSYS2 on `PATH`.

## 2. Python environment

```bash
uv venv --python 3.12
uv sync
.venv\Scripts\python.exe -m ipykernel install --user --name hyperspectral-brdf --display-name "Python (.venv BRDF)"
```

What `uv sync` does:

- Builds `vendor/pyprosail` with meson-python and `numpy.f2py`, then installs it.
- Installs the project package `publication_spectral_data` from `src/` in editable mode.
- Installs the `dev` group by default: `pytest`, plus the pure-Python `prosail` package used for cross-checks.

Check the build:

```bash
uv run python -c "import pyprosail; r = pyprosail.run_all(1.5,40,8,0,0.01,0.009,0.5,2.5,0.01,30,10,0,2,60,0); print(r.rsot.shape)"
# (2101,)
```

## 3. R environment (optional, for the R cross-check)

```r
renv::restore()   # reads renv.lock: prosail (jbferet, GitLab), ggplot2, renv
```

To install from scratch: `renv::install("gitlab::jbferet/prosail")`. This pulls about 95 dependencies, takes around 5 minutes, and builds `prosail` itself from source.

## 4. Run things

| Task | Command |
|---|---|
| Interactive app | `uv run streamlit run app/streamlit_app.py` → http://localhost:8501 |
| Restrict the app to this machine | add `--server.address localhost` |
| Tests | `uv run pytest` |
| Python cross-check | `uv run python scripts/crosscheck_prosail.py` |
| R cross-check | `Rscript scripts/crosscheck_prosail.R`, then re-run the Python script to merge |
| BRDF analysis document | `quarto render BRDF.qmd` |
| Manuscript | `quarto use template quarto-journals/elsevier` (once), then `quarto render article.qmd --to elsevier-pdf` |

## 5. Using the engine from your own code

```python
from publication_spectral_data.prosail_engine import CanopyParams, simulate, brdf_grid
from publication_spectral_data.indices import compute_index

params = CanopyParams(lai=3.0, cab=45, lidfa=60)
spec = simulate(params, sza=30, vza=10, raa=0)   # dict of spectra + "wavelength"
print(compute_index("NDVI", spec["rsot"]))

grid = brdf_grid(params, sza=30, vza_values=range(0, 81, 10), raa_values=range(0, 360, 10),
                 factor="resv", index="NDVI")     # tidy DataFrame: vza, raa, value
```

Next: [Architecture](Architecture.md).
