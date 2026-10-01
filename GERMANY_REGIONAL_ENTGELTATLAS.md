# Germany: regional 2025 Entgeltatlas (controlled rollout)

**Current coverage:** The EarnWage national Germany snapshot contains **27
approved occupation–Berufsgattung mappings** and published national monthly
median remuneration values. The 16 federal states are available as optional
selectors. **Regional occupation wages have NOT been imported** as of this
development stage. The API reports `pending_verified_regional_import`,
zero verified regional salary cells, and never copies the national value to
a selected region.

The public [Germany salary lookup](https://gilpereirapt.github.io/Global-Purchasing-Power-API/germany.html)
shows available, approved **national** medians, an optional state selector,
and a clear regional-data pending state. It does **not** claim to know the
salary of a profession in a selected federal state.

## Why a strict import is required

Official [BA Entgeltatlas documentation](https://www.arbeitsagentur.de/hilfe-entgeltatlas)
confirms the statistical population is social-security-covered full-time
employment and that the product reports occupational *aggregates*, not
salaries for individuals holding each named job. If a regional Berufsgattung
cell is based on fewer than 500 employees, the BA system may offer a wider
`Berufsgruppe` or geographic fallback. It may also display right-censored
`>8050 EUR` values at the 2025 contribution ceiling.

The EarnWage import must therefore verify **every** cell's exact occupational
aggregate, requirement level, original selected state, uncensored median,
reference period, and official evidence reference. A wider group or different
region must never be represented as the requested exact-scope state median.

The public third-party [Entgeltatlas API technical documentation](https://github.com/AndreasFischer1985/entgeltatlas-api)
lists state parameter values and technical endpoints but is **not** an
official service contract. The official endpoint returned HTTP 403 during
public verification; no unattended scraping or embedded/shared third-party
credentials have been used.

## Importing an individually verified state record

Create a private JSON input under an appropriate working directory. The
following shows *field structure only*. **It is not real regional wage data**
and must never be published as such.

```json
{
  "schema": 1,
  "country": "DE",
  "reference_period": "2025",
  "records": [
    {
      "occupation": "software_developer",
      "state": "BY",
      "value": 0,
      "reference_period": "2025",
      "currency": "EUR",
      "unit": "EUR/month",
      "measure": "median",
      "precision": "occupation_specific_kldb_berufsgattung_no_fallback",
      "aggregation_level": "Berufsgattung",
      "evidence_page_id": "134894",
      "source_url": "https://web.arbeitsagentur.de/entgeltatlas/beruf/134894",
      "state_ba_region_id": 12,
      "profession_title": "REPLACE WITH EXACT APPROVED NATIONAL RECORD LABEL",
      "occupational_aggregate": "REPLACE WITH EXACT APPROVED NATIONAL AGGREGATE",
      "requirement_level": "REPLACE WITH EXACT APPROVED NATIONAL LEVEL",
      "raw_ba_evidence_reference": "REPLACE WITH HUMAN-REVIEWED SOURCE RECORD IDENTIFIER"
    }
  ]
}
```

The validator explicitly rejects `value: 0`, any scope or level mismatch,
a different evidence-page ID, an unknown state, invalid numbers, duplicate
profession/state records and censored values. The template must be replaced
with a **verified** official 2025 state observation and identical approved
national profession metadata before import.

When genuine, source-reviewed records are obtained, run:

```bash
python -m app.de_entgeltatlas_states_import \
  --reviewed-input /private/entgeltatlas-states-reviewed-2025.json \
  --output data/de_entgeltatlas_states_2025.json
python -m pytest -q
```

Only submit the aggregate-only output after the source review and validation.
No automated workflow will fabricate missing state observations.

## Implemented endpoints

- `GET /v1/regions/DE` — all 16 federal states, regional selection optional.
- `GET /v1/earnwage/overview?country=DE&occupation=software_developer&region=BY`
  — a verified national occupational wage independent of the regional wage's
  explicit unavailable status.
- `GET /v1/de/entgeltatlas/regional/coverage` — real regional coverage,
  zero until the audited source snapshot is imported.
- `GET /v1/earnwage/coverage` — only actually imported state-profession
  cells count; national observations do not inflate regional coverage.

Production deployment remains independently gated. Publishing GitHub changes
and the static web page does not update the private Passenger API or its DB.
