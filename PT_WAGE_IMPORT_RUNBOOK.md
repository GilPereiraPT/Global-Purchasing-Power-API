# Portugal: importing verified salaries by CPP occupation

Status: **importer prepared, NO official PT profession wage snapshot imported**.
No salary is asserted here unless the INE 0010385 raw JSON was actually
inspected and its individual four-digit CPP-2010 category confirmed.

## Data provenance

- Publisher: INE; underlying source MTSSS/GEP, Quadros de Pessoal.
- Indicator: **0010385**; gain (not contractual base pay, net salary, or a
  statutory DGAEP public-sector pay scale) by national geography and CPP.
- https://www.ine.pt/xurl/indx/0010385/PT
- Official JSON:
  https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0010385&lang=PT
- Metadata:
  https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp?varcd=0010385&lang=PT
- Original open-data record / licence CC BY 4.0:
  https://dados.gov.pt/pt/datasets/ganho-medio-mensal-eur-7

**Important:** the source metadata URL/description was confirmed, but the
live INE 0010385 response shape/categories could not be fetched from the
assistant's external browsing session. Inspect BEFORE approving a mapping.
The published GEP headline 2024 PDF mainly contains 1- and 2-digit groups;
these cannot be used as wages for individual EarnWage jobs. This importer
rejects them. Portugal must be the national geography; it rejects a source
labelled Continente, Lisboa, Norte, etc. rather than calling it all Portugal.

## Stage 1 — inspect official source (no production write)

From the repo root in a terminal with Python requirements installed:

```bash
python -m app.pt_occupation_wages --fetch --inspect > ine-0010385-inspection.json
```

Or after downloading the INE response yourself as `ine-0010385-raw.json`:

```bash
python -m app.pt_occupation_wages --source ine-0010385-raw.json --inspect
```

A manual GitHub Actions workflow, **Inspect INE Portuguese occupation wages**,
will perform the same read-only source query and print the geography, year,
and available classification dimensions in private build logs. This does NOT
import anything and does not write the server database.

Verify the returned field names `dim_N` and `dim_N_t` and its original
four-digit CPP-2010 categories. If the dataset only has large 1-/2-/3-digit
groups, stop. Find a different freely reusable detailed source; do not
generate fictional doctor/nurse/psychologist differences.

## Stage 2 — approve the source's ACTUAL correspondence

Create a local file `pt-cpp-approved.json`, with the **real** geographic
code, occupation dimension, CPP codes and original labels exactly copied
from inspection:

```json
{
  "indicator": "0010385",
  "occupation_dimension": "dim_N",
  "geography": {"code": "VERIFIED_PT_CODE", "label": "Portugal"},
  "occupations": [
    {"occupation": "nurse", "cpp_code": "FOUR_DIGITS", "cpp_label": "ORIGINAL INE LABEL"}
  ]
}
```

This example contains deliberately invalid placeholders. No occupation code,
region code or salary amount is asserted or manufactured by the importer.
An INE CPP code describing only a subclass (e.g. one medical specialty)
MUST NOT be presented as the national average for all doctors. If the
verified category isn't equivalent to the selected EarnWage job, don't map it.

## Stage 3 — export a vetted snapshot

```bash
python -m app.pt_occupation_wages --source ine-0010385-raw.json \
  --mapping pt-cpp-approved.json --export data/pt_occupation_wages.json
```

The exporter checks the indicator, the salary concept, code+label+geography
exact match, strictly four-digit CPP classification, positive numbers, years,
and no duplicate profession/year. Missing/confidential cells are omitted,
not converted to zero. It refuses to overwrite a snapshot silently.

The output includes the original source URL and licence for every observation,
and is strictly monthly EUR **ganho médio**; any annualised display is
marked **monthly × 12 for comparison**, not verified 13th/14th payments.
No other source/major-group salaries are overwritten.

## Stage 4 — controlled server deploy after backup

First create a verified private backup with the existing EarnWage Data Manager.
Then deploy the changed Python app files and the *validated* snapshot at
`data/pt_occupation_wages.json`. Restart the Passenger Python app. Its
startup loads the snapshot idempotently into the existing `GPP_CACHE_DB`
without replacing World Bank/Eurostat data or US/CA wages. There is no
automatic remote import while the source schema/codes are unverified.

Check:
- `GET /v1/earnwage/overview?country=PT&occupation=nurse`
- `GET /v1/earnwage/coverage`
- `GET /v1/data-inventory`

A profession without a verified match remains unavailable, even if the
ILOSTAT group-2 reference is already present. The Data Manager's WDI
buttons are not Portuguese occupational wage importers.

## Next sources

The same validated snapshot contract can be adapted for ONS ASHE four-digit
SOC and other official country sources, but each country needs its own source
identifier, scope, units, occupation crosswalk, and licence validation.
