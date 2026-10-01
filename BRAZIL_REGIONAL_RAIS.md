# Brazil: RAIS 2025 occupation-specific wages by UF

The API and EarnWage clients now support an **optional UF** (state / Distrito Federal)
when the country is `BR`. Occupation-specific results are based on the exact
six-digit CBO 2002 occupation codes already curated for Brazil.

## Source and statistical scope

- Official underlying source: [MTE RAIS 2025](https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2025/rais-2025).
- Published CBO-by-UF tables: [99K](https://99k.com.br/), which provides
  public aggregations of the MTE RAIS microdata.
- Measure: **median of December 2025 monthly remuneration**, BRL,
  formal employment links active on 31 December 2025 with **contracted
  weekly hours 40–44**. Excludes PJ, independent and informal work.
- Result provenance retains the **original occupation-page URL for every row**.
  This is a third-party RAIS-derived aggregation, *not* a direct MTE table.
- No regional value is inferred from the national median, other states, or
  a non-identical CBO occupation. At least 20 links are required per imported
  cell as an extra conservative publication screen.

## Verified imported scope

- 38 directly mapped occupations;
- all 27 Brazilian UFs have at least some eligible observations;
- 993 validated occupation-by-UF medians;
- the two national composite professions (`manager` and
  `secondary_teacher`) are excluded from the state dataset because
  combining published medians would not produce a valid state median.

## Endpoints

- `GET /v1/regions/BR`: optional UF selector with all 27 UFs.
- `GET /v1/earnwage/overview?country=BR&occupation=accountant&region=SP`:
  returns `regional_occupation_wage` separately from
  `national_occupation_wage`.
- `GET /v1/earnwage/coverage`: regional salary coverage is counted independently.
- `GET /v1/br/rais/regional/coverage`: dedicated regional import audit.
- `GET /v1/earnwage/compare?...&region_a=SP`: same regional context
  in a two-country comparison.

Both FastAPI and production native WSGI load the committed
`data/br_rais_2025_states.json` snapshot when available. Production will not
receive GitHub changes until the user's **production deployment is enabled
or the Data Manager updates the deployed runtime**.

## Direct web access despite an outdated API

[EarnWage Brazil lookup](https://gilpereirapt.github.io/Global-Purchasing-Power-API/brazil.html?occupation=accountant&uf=SP)
uses a compact public snapshot under `docs/data/br-rais-2025-states.json`,
so it can display published regional medians even if the production API
has not been deployed yet. Static and canonical snapshots must stay identical,
enforced by `tests/test_br_rais_web_snapshot.py`.

## Reproducible refresh

The GitHub Actions workflow `.github/workflows/import-brazil-rais-states.yml`
collects the public CBO state pages and only publishes a new snapshot
after checking **every source page**, its CBO code, table structure and
minimum coverage. Failures stop publication; they do not introduce partial
or fabricated estimates. Any reimport may require updating the static
web snapshot at the same time so the parity test continues to pass.

These figures are **not** validated personal after-tax earnings and should
not be used for purchasing-power comparisons without matching regional
living costs and the relevant tax context.
