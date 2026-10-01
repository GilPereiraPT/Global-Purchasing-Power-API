# India PLFS 2025 — audited microdata import

The official calendar-year **PLFS 2025** catalog identifies the first-visit
person file `cperv12025` (1,148,634 records) and its codebook:
https://microdata.gov.in/NADA/index.php/catalog/284

The directly downloadable supplementary documentation is listed at:
https://microdata.gov.in/NADA/index.php/catalog/284/related-materials

Relevant documents: **FV_Data_LayoutPLFS_2025**, **Indian_States_and_UTs_CodeName**,
**README2025** and the first-visit field-staff instruction manuals. Use the official
portal's **Get Microdata** facility and confirm applicable terms before downloading
the individual data. The raw microdata must NOT be committed to the repository.

## Scope

This importer estimates *descriptive, weighted average preceding-calendar-month
earnings* among people whose **current weekly status** identifies regular
wage/salaried employment, using `acws`, `ocu_cws`, `ern_reg`, `mult`, `visit`
and `st`. It does not mix this measure with self-employed earnings or daily casual
wages. It does **not** claim design-based standard errors or statistical confidence.

Results are separated by audited NCO-2015 occupation code and by:
- India as a whole;
- the respondent's officially coded State/Union Territory.

Even when an NCO code resembles an EarnWage occupation, it is **not automatically
mapped**. An independently reviewed NCO-2015 ↔ EarnWage occupation concordance
is still required. The currently shipped importer therefore publishes NCO-coded
statistics to dedicated endpoints, not to `national_occupation_wage`.

## Obtain and review official files

1. Obtain the official **first-visit person-level** dataset for calendar 2025
   through the NADA portal. Read `README2025` and the official layout; convert
   fixed-width/TXT files to CSV using that documented layout. Do not infer offsets.
2. Obtain **Indian_States_and_UTs_CodeName.xlsx** from the same catalog.
   Transcribe its exact official numeric State/UT code→name combinations into
   `states` below. Use string keys with leading zeroes omitted.
3. Obtain the official NCO-2015 classification and validate each code and label
   present in your intended analysis. Insert only those validated codes into
   `occupations` below. A broad NCO category must retain its broad title.
4. Review the 2025 first-visit instructions to confirm the CWS salaried-status
   codes `31`, `71`, `72`, the visit indicator `1` and multiplier scaling.
   The importer rejects any other manifest assumptions. Survey revisions
   require source review and a code change.

Create a **local, reviewed** manifest (illustrative structural example — replace
all examples with verified official codes and real labels):

```json
{
  "survey": "DDI-IND-NSO-PLFS-Jan2025-Dec2025",
  "verified_person_file": "cperv12025",
  "official_state_crosswalk_reviewed": true,
  "first_visit_code": "1",
  "regular_employee_cws_codes": ["31", "71", "72"],
  "multiplier_scale": 100,
  "states": {"<official state code>": "<verified State/UT name>"},
  "occupations": {"<official NCO 2015 code>": "<verified official occupation label>"}
}
```

The placeholders above are **not** usable until replaced with reviewed values.
Keep the manifest and the raw individual data outside publicly served paths.

## Offline import and secure release

```bash
export GPP_CACHE_DB=/absolute/private/path/earnwage.sqlite3
python -m app.in_plfs_microdata \
  --person-csv /private/plfs2025/cperv12025.csv \
  --manifest /private/plfs2025/reviewed_codes.json \
  --output data/in_plfs_2025_nco.json
```

The command **does not** download respondent data from NADA. It requires files
obtained under the data portal's applicable conditions. The exported file contains
*aggregated data only*, including a checksum of the reviewed manifest, counts and
a provenance link. Never commit respondent-level CSVs or the private source ZIP.

Disclosure guardrails (internal conservative product thresholds, **not**
official MoSPI thresholds): each released cell needs at least 50 sampled
respondents, approximate effective n >=30 and at least 10 distinct observed
FSU identifiers. Zero earnings are retained where legitimately recorded.
Missing/unmapped codes and state crosswalk gaps cannot be filled with guesses.
These checks are only a minimum publication screen, **not** a replacement
for survey-design variance, sample-validity or external disclosure review.

For production, review the aggregates, then commit
`data/in_plfs_2025_nco.json`. The API reads that file into its persistent
SQLite on startup.

## Public endpoints

```
GET /v1/in/plfs/nco/coverage
GET /v1/in/plfs/nco/{verified_nco_code}
GET /v1/in/plfs/nco/{verified_nco_code}?state={official_state_code}
GET /v1/in/plfs/earnings
GET /v1/in/wage-sources
```

Until a validated aggregate snapshot is present, NCO coverage states
`not_imported` and individual queries explicitly report `unavailable`.
Do not mistake the national all-occupation PLFS headline figure for
profession-specific earnings.
