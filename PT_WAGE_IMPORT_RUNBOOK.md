# Portugal: importing verified salaries by CPP occupation

Status: **importer prepared, NO official PT profession wage snapshot imported**.

## Source audit — actual official JSON captured on 27 September 2026

The official INE JSON 0010385 was downloaded through a user's local
browser, overcoming GitHub Actions' three `ConnectTimeout` failures.
**This particular official indicator CANNOT fill an exact profession wage
cell**. Verified structural facts of the *full* response:

- `IndicadorCod=0010385`; source is GEP Quadros de Pessoal.
- `UltimoPref=2022`; just one year (`Dados.2022`); 3,440 records.
- 344 distinct geography codes, including `PT` = `Portugal`.
- `dim_3` contains only codes `1` through `9` and `T` (total),
  each with 344 rows. **No CPP four-digit occupation appears at all.**
- National category `2` (all intellectual and scientific specialists)
  has published mean monthly gain EUR 2,094.56 for 2022. **Not the wage
  of doctor, nurse, psychologist, nor any particular specialist.**

Do NOT feed this JSON into the exact-occupation exporter. It correctly
rejects 1-digit profession mappings. Do NOT rerun GitHub inspection for
this indicator in the hope of generating 4-digit observations; a successful
download will have the same aggregate-only scope until INE changes the
published indicator's dimensions. The complete raw JSON was **not**
committed into repository or imported to production.

### Next source research

Seek a separately published, legitimately reusable dataset with four-digit
CPP/ISCO occupational gain and nationally identified coverage. GEP Quadros de
Pessoal 2014–2024 public tables are chiefly aggregated (1 and 2 digits).
DGAEP SRAP offers **public statutory career/category/pay-position scales**,
which can be collected separately with its official version and pay concept;
they are not national observed profession means. UK ONS ASHE four-digit SOC
is a separate official source candidate for GB; do not relabel ONS figures
as Portuguese earnings.


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

## If GitHub Actions reports `httpx.ConnectTimeout`

This is a failed network connection to the INE HTTP endpoint, not a
salary-record or CPP mapping failure. The inspector now retries up to three
times with independently bounded connect/read timeouts and safe errors. If
all three attempts fail, **no salary is imported**, and rerunning indefinitely
is not recommended.

From a computer that can access the published INE JSON, open the exact
[official data URL](https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0010385&lang=PT).
If your browser displays a JSON document, use **Save As** to store
`ine-0010385-raw.json` (UTF-8, complete file; do not save the HTML
indicator webpage). Then use:

```bash
python -m app.pt_occupation_wages --source ine-0010385-raw.json --inspect
```

Only a source-backed, inspected JSON response can be used for the later
mapping/export; **do not commit mock/test fixtures as real wages**.
The open-data catalogue at https://dados.gov.pt/pt/datasets/ganho-medio-mensal-eur-7/
is a publisher catalogue, not a guarantee that its linked resource is
reachable from GitHub's IP range or a permanent copy hosted elsewhere.
Do not replace the INE URL with an unrelated salary series when a connection
fails.

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
