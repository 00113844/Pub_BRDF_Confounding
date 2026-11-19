# Cross-check: run the jbferet R prosail package (PROSPECT-PRO + 4SAIL) on the
# case matrix written by scripts/crosscheck_prosail.py, using the same soil
# spectrum as the Fortran code, and write spectra every 10 nm for comparison.
#
# Usage (from the repository root, after the Python script has run once):
#   Rscript scripts/crosscheck_prosail.R
#   uv run python scripts/crosscheck_prosail.py   # merges the R results
#
# Install the package with: renv::install("gitlab::jbferet/prosail")

if (!requireNamespace("prosail", quietly = TRUE)) {
  stop("R package 'prosail' (jbferet) is required: renv::install('gitlab::jbferet/prosail')")
}

logs <- file.path("results", "logs")
cases <- read.csv(file.path(logs, "crosscheck_cases.csv"))
soil <- read.csv(file.path(logs, "crosscheck_soil.csv"))
step_nm <- 10
keep <- soil$wavelength %% step_nm == 0

run_case <- function(case) {
  # Same soil as the Fortran code: soil_scale * (psoil * dry + (1 - psoil) * wet)
  rsoil <- case$soil_scale * (case$psoil * soil$dry + (1 - case$psoil) * soil$wet)
  # PROSPECT-PRO with lma set (prot = cbc = 0) is the PROSPECT-5 parameterisation
  # apart from the optical constants; anthocyanins are 0 as in PROSPECT-5.
  input_prospect <- data.frame(
    chl = case$cab, car = case$car, ant = 0, brown = case$cbrown,
    ewt = case$cw, lma = case$cm, n_struct = case$N
  )
  refl <- prosail::prosail(
    input_prospect = input_prospect,
    type_lidf = case$typelidf, lidf_a = case$lidfa, lidf_b = case$lidfb,
    lai = case$lai, hotspot = case$hspot,
    tts = case$sza, tto = case$vza, psi = case$raa,
    rsoil = rsoil
  )
  do.call(rbind, lapply(c("rsot", "rdot", "rsdt", "rddt"), function(factor) {
    data.frame(
      case_id = case$case_id,
      factor = factor,
      wavelength = soil$wavelength[keep],
      value = as.numeric(refl[[factor]])[keep]
    )
  }))
}

spectra <- do.call(rbind, lapply(seq_len(nrow(cases)), function(i) run_case(cases[i, ])))
out <- file.path(logs, "crosscheck_r_spectra.csv")
write.csv(spectra, out, row.names = FALSE)
message(sprintf("Wrote %d rows for %d cases to %s (prosail %s)",
                nrow(spectra), nrow(cases), out, as.character(packageVersion("prosail"))))
