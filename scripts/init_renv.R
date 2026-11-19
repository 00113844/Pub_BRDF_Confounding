if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages("renv", repos = "https://cloud.r-project.org")
}

if (!file.exists("renv.lock")) {
  renv::init(bare = TRUE)
}

message("renv initialized. Install analysis packages with renv::install() and record them with renv::snapshot().")
