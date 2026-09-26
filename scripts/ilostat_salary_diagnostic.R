# Read-only first salary dataset validation using the official Rilostat 2.5 client.
# Do not publish or treat a dataset's catalogue end year as coverage for every country.
suppressPackageStartupMessages(library(Rilostat))
args <- commandArgs(trailingOnly = TRUE)
id <- if (length(args)) args[[1]] else "EAR_EMTA_SEX_OCU_NB_A"
allowed <- c("EAR_EMTA_SEX_OCU_NB_A", "EAR_EMTA_SEX_OCU_CUR_NB_A")
if (!id %in% allowed) stop("Dataset is not in the two approved salary indicators")
countries <- c("PRT","ESP","DEU","FRA","GBR","IND","BRA","PAK",
               "NLD","CHE","ITA","IRL","USA","CAN")
dir.create("diagnostics", recursive = TRUE, showWarnings = FALSE)
cat("Rilostat:", as.character(packageVersion("Rilostat")), "dataset:", id, "\n")
tryCatch({
  dat <- get_ilostat(id = id, segment = "indicator", type = "code",
                     best_source = "all", time_format = "raw",
                     filters = list(ref_area = countries, timefrom = "2020"),
                     cache = FALSE, quiet = FALSE)
  if (is.null(dat) || !nrow(dat)) stop("No observations for selected countries since 2020")
  dat <- as.data.frame(dat)
  required <- c("ref_area","time","sex","obs_value")
  if (!all(required %in% names(dat))) {
    stop("Missing dataset columns: ", paste(setdiff(required, names(dat)), collapse=", "))
  }
  cat("Returned rows:", nrow(dat), "\n")
  cat("Columns:", paste(names(dat), collapse=", "), "\n")
  write.csv(utils::head(dat, 100), paste0("diagnostics/", id, "_sample.csv"),
            row.names=FALSE, na="")
  count <- function(column, limit=40L) {
    if (!column %in% names(dat)) return(invisible(NULL))
    vals <- as.character(dat[[column]])
    tab <- sort(table(vals, useNA="ifany"), decreasing=TRUE)
    cat("\n", column, " distinct=", length(tab), "\n", sep="")
    print(utils::head(tab, limit))
    invisible(NULL)
  }
  for (col in c("ref_area","time","sex","classif1","classif2",
                "currency","indicator","source","best_source",
                "obs_status","note_source")) count(col)
  countries_report <- do.call(rbind, lapply(countries, function(country) {
    subset <- dat[as.character(dat$ref_area) == country, , drop=FALSE]
    years <- as.character(subset$time)
    data.frame(country=country, rows=nrow(subset),
               first_period=if(length(years)) min(years) else "",
               latest_period=if(length(years)) max(years) else "",
               occupation_codes=if("classif1" %in% names(subset))
                 length(unique(as.character(subset$classif1))) else NA_integer_,
               stringsAsFactors=FALSE)
  }))
  write.csv(countries_report, paste0("diagnostics/", id, "_coverage.csv"),
            row.names=FALSE, na="")
  print(countries_report, row.names=FALSE)
  # Keep the observed classification combinations; never infer currency from a label.
  detail_columns <- intersect(c("ref_area", "time", "sex", "classif1",
                                 "classif2", "currency", "indicator", "source",
                                 "obs_status"), names(dat))
  if (length(detail_columns)) {
    detail <- unique(dat[, detail_columns, drop = FALSE])
    detail[] <- lapply(detail, as.character)
    write.csv(detail, paste0("diagnostics/", id, "_classification_matrix.csv"),
              row.names = FALSE, na = "")
    cat("Distinct classification combinations:", nrow(detail), "\n")
  }
  if ("classif1" %in% names(dat)) {
    codes <- unique(as.character(dat$classif1))
    codes <- codes[!is.na(codes) & nzchar(codes)]
    exact <- codes[grepl("(^|_)ISCO08_[0-9]{4}$", codes)]
    major <- codes[grepl("(^|_)ISCO08_[0-9]$", codes)]
    cat("ISCO-08 exact four-digit codes:", length(exact), "\n")
    cat("ISCO-08 major-group codes:", length(major), "\n")
    cat("Exact codes:", paste(exact, collapse = ", "), "\n")
  }
  cat("Diagnostic complete: no salaries published or imported.\n")
}, error=function(e) {
  message("Official salary dataset diagnostic failed: ", conditionMessage(e))
  quit(status=1L)
})
