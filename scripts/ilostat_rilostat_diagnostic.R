# Inspect ILOSTAT with the official Rilostat client, independently of Python.
# Read-only: no salary database writes or publication.
suppressPackageStartupMessages(library(Rilostat))

dir.create("diagnostics", recursive = TRUE, showWarnings = FALSE)

tryCatch({
  cat("Rilostat version:", as.character(packageVersion("Rilostat")), "\n")
  cat("Requesting official ILOSTAT indicator catalogue via get_ilostat_toc()\n")
  toc <- get_ilostat_toc(segment = "indicator", lang = "en",
                         cache_update = TRUE, quiet = FALSE)
  cat("Catalogue rows:", nrow(toc), "\n")
  cat("Catalogue columns:", paste(names(toc), collapse = ", "), "\n")
  required <- c("id", "indicator.label")
  if (!all(required %in% names(toc)) || nrow(toc) == 0L) {
    stop("Official Rilostat catalogue empty or missing required columns")
  }
  selected <- grepl("^EAR_", toc$id) &
              (grepl("earnings|wage|salary", toc$indicator.label,
                     ignore.case = TRUE) |
               grepl("EMTA", toc$id, fixed = TRUE))
  columns <- intersect(c("id", "indicator.label", "freq", "data.end",
                          "last.update"), names(toc))
  candidate <- as.data.frame(toc[selected, columns, drop = FALSE])
  candidate[] <- lapply(candidate, as.character)
  write.csv(candidate, "diagnostics/ilostat_earnings_candidates.csv",
            row.names = FALSE, na = "")
  cat("Earnings-related annual/other candidates:", nrow(candidate), "\n")
  print(utils::head(candidate, 30), row.names = FALSE)
  matching <- candidate[grepl("EAR_EMTA_SEX_OCU_CUR_NB_A", candidate$id,
                              fixed = TRUE), , drop = FALSE]
  cat("Requested dataset present:", nrow(matching) > 0L, "\n")
  if (nrow(matching)) print(matching, row.names = FALSE)
  if (nrow(candidate) == 0L) stop("Catalogue available but no earnings candidates")
}, error = function(e) {
  message("Rilostat diagnostic failed: ", conditionMessage(e))
  quit(status = 1L)
})
