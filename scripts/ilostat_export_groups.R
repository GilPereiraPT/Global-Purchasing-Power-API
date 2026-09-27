# Official Rilostat client: export actual observations for strict Python validation.
suppressPackageStartupMessages(library(Rilostat))
countries <- c("PRT","ESP","DEU","FRA","GBR","IND","BRA","PAK",
               "NLD","CHE","ITA","IRL","USA","CAN")
dataset <- "EAR_EMTA_SEX_OCU_CUR_NB_A"
dat <- get_ilostat(id=dataset, segment="indicator", type="code",
                   best_source="all", time_format="raw",
                   filters=list(ref_area=countries, timefrom="2020"),
                   cache=FALSE, quiet=FALSE)
if (is.null(dat) || !nrow(dat)) stop("Official ILOSTAT dataset returned no rows")
dir.create("diagnostics", showWarnings=FALSE)
write.csv(as.data.frame(dat), "diagnostics/ilostat_groups_raw.csv",
          row.names=FALSE, na="")
cat("Official ILOSTAT rows exported:", nrow(dat), "\n")
