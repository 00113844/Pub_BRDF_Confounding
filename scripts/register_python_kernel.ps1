$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
& $python -m ipykernel install --user --name hyperspectral-brdf --display-name "Python (.venv BRDF)"
