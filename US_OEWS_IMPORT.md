# US BLS OEWS — complete importer

EarnWage includes a complete offline importer for the official U.S. Bureau of Labor Statistics Occupational Employment and Wage Statistics (OEWS) release.

Official release catalogue: https://www.bls.gov/oes/tables.htm

For May 2025 BLS publishes national, state, metropolitan/nonmetropolitan, national industry/ownership and an "All data" download. The importer preserves the source fields and never fabricates missing or suppressed values.

## Import on the production server

Use the same persistent SQLite file used by the Passenger application:

```bash
export GPP_CACHE_DB=/absolute/private/path/earnwage.sqlite3

# Preferred when the official ZIP is already downloaded:
python -m app.us_oews --zip /path/to/oesm25all.zip --year 2025

# Or let the CLI attempt the official BLS download:
python -m app.us_oews --download --year 2025
```

The BLS site has previously returned HTTP 403 to some automated/cloud clients. That is why a local ZIP path is a first-class supported mode rather than a fallback.

A single official workbook can also be imported:

```bash
python -m app.us_oews --xlsx /path/to/national.xlsx --year 2025
```

By default, reimporting a release replaces rows for that publication year. Use `--append` only when intentionally adding another workbook from the same release.

## Stored fields

One SQLite row represents one published OEWS occupation/scope observation. It retains:

- reference period and publication year;
- source workbook;
- area code/title/type and primary state;
- NAICS code/title, industry group and ownership code where published;
- SOC occupation code/title and occupation group;
- employment and precision fields where published;
- hourly mean, annual mean;
- hourly and annual 10th, 25th, median, 75th and 90th percentile wages;
- BLS source URL.

BLS suppression markers such as `*`, `**` and `#` are stored as SQL NULL. They are never replaced with estimates.

## API

After import:

```text
GET /v1/us/oews/coverage
GET /v1/us/oews/occupations?q=software&limit=50
GET /v1/us/oews/wages/15-1252
GET /v1/us/oews/wages/15-1252?state=CA
GET /v1/us/oews/wages/15-1252?area=41860&year=2025
```

The existing curated route remains unchanged:

```text
GET /v1/salaries/US/software_developer
```

That curated route uses only explicitly approved EarnWage↔SOC mappings. The OEWS routes expose the full official SOC catalogue without pretending that every BLS occupation already has an EarnWage translation/mapping.

## Operational notes

The full OEWS release is large. The importer:

- streams XLSX rows into SQLite in batches;
- applies ZIP path-traversal checks;
- caps download and expanded ZIP sizes;
- indexes SOC, occupation title and geography;
- never performs the import inside a public HTTP request.

The SQLite database should live outside `public_html` and must be writable/readable by both the CLI/cron user and Passenger process.
