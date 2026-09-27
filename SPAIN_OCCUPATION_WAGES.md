# Spain wage import: INE EES 2022, evidence-gated

## Verified and imported: annual EAES 2008–2024 **BROAD GROUP CONTEXT ONLY**

From the actual official INE JSON for **Table 28186 — Sexo y grupos
principales de ocupación**, supplied as `28186.json` and checked against
INE's national 2024 release, the repository now ships
`data/es_ine_eaes_28186.json`. Source:
https://www.ine.es/jaxiT3/Tabla.htm?t=28186

The snapshot has exactly **54 series** = 17 major occupation groups
CNO-11 `A`–`Q` plus total, each with both sexes, women and men;
2008–2024; **918 original year × group × sex cells**, comprising **856
published amounts**, **62 null/suppressed** and **29 published with
small-sample high-variability flags**. Military group Q has no values.
Currency EUR, measure national **mean gross annual wage**, not gross
monthly wage, not median and NOT specific to 40 EarnWage occupations.

The source encodes a published small-sample flag as a NEGATIVE number
(e.g. J / women / 2024 = -24001.36), and supplies an explicit `Notas`
explanation (100 to 500 sample observations). The importer preserves the
flag and presents **positive 24001.36 EUR/year** with
`sample_quality=sample_100_to_500_high_variability`. A null value
with the source's `<100` note remains `status=suppressed`, value null.
It never exposes negative earnings or silently fills absent categories.

Endpoints (FastAPI and production native Passenger WSGI):
- `GET /v1/es/earnings/groups`
- `GET /v1/es/earnings/groups/B?sex=both&start_year=2008&end_year=2024`
- `GET /v1/es/earnings/groups/H?sex=women&start_year=2024&end_year=2024`

Group B **40,554.53 EUR/year in 2024** includes health AND education
scientific/intellectual specialists. Group H **19,479.94 EUR/year**
includes health and personal-care services workers. Neither is a
doctor, nurse or psychologist salary. Salary cards, exact-occupation
coverage, and occupation comparisons deliberately do not import these
groups. The data inventory has an *independent* ES group count. This
snapshot is included in GitHub source but needs the user's usual
server code deployment to appear at the live API.

Reuse: INE's original statistical information is generally CC BY 4.0
with attribution, including commercial use unless an exception applies.
https://www.ine.es/datosabiertos/
Attribution: `Fonte: Instituto Nacional de Estadística (INE), Encuesta
Anual de Estructura Salarial, tabla 28186, www.ine.es. Dados tratados
pela EarnWage.` This is not an INE-endorsed application.



## Confirmed sources

Official INE EES annual 2024 public results (published 28 May 2026)
do NOT establish doctor/nurse/psychologist wages: published
occupation tables are primarily major CNO-11 groupings.
https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177025&idp=1254735976596&menu=resultados

INE *Encuesta cuatrienal de estructura salarial 2022* definitive,
published 23 September 2024, supplies **free anonymised microdata**. The
**actual complete package `datos_2022.zip` was inspected on 27 September
2026**, directly from the official public files: no need to ask for it
again. Its `Leeme.txt` documents TAB, fixed-width TXT, R, SAS, SPSS,
Stata and parquet versions and a JSON/XLSX variable design. **The
TAB contains 240,490 employee records, but only major-group `CNO1`,
encoded `A0` through `Q0`, not individual 4-digit CNO-11 occupations.**
The source dictionary `dr_EES_2022.json` explicitly states `CNO1`
is `GRUPO PRINCIPAL CNO-11`, length two. The SAS `TCNO` codelist
confirms A0–Q0. Therefore, *this public microdata package cannot
deliver doctor/nurse/psychologist-specific wages*; intersecting `B0`
and CNAE healthcare is only a broad healthcare-sector specialist cohort,
not a single profession. Never commit the individual-level microdata.

### Official annual wage formula successfully replicated

The archive contains a methodological Word document, *EES22 Obtención
de los resultados publicados a partir de los microdatos web.doc*,
which describes derived variables:
```text
DIASRELABA = min(365, DRELABAM * 30.42 + DRELABAD)
DIASANO = DIASRELABA - DSIESPA2 - DSIESPA4
SALANUAL = 365 / DIASANO *
           (RETRINOIN + RETRIIN + VESPNOIN + VESPIN)
national_weighted_mean =
   sum(SALANUAL * FACTOTAL) / sum(FACTOTAL)
```
Computed on all **240,490** rows without excluded/invalid cases:
`26948.865124103464 EUR/year`, rounding to the INE published 2022
`26,948.87 EUR/year` national gross annual mean:
https://www.ine.es/dyngs/Prensa/EES2022.htm
Published 2022 group B salary EUR 37,456.34/year was also reproduced
(EUR 37,456.34 rounded). This validates the salary-variable use,
annualisation and supplied `FACTOTAL` weights, but **cannot resolve
the occupation category suppression**. The INE warns that disclosure
masking may cause small rounded discrepancies in subgroups; don't
claim exact equivalence for every sex/region cell. No raw microdata
were uploaded to the public repository.

Public sources with four-digit occupation salary data still need
research, or an INE request for further anonymised detail on the
applicable terms.

INE explicitly offers requests for **more detailed anonymised data**
subject to review, terms and possible payment where the public file
cannot supply needed disaggregation. No inference from public generic
occupation groups to individual occupation wages is permissible.

Official INE reuse: https://www.ine.es/dyngs/AYU/index.htm?cid=125
The general CC BY 4.0 statistical-data reuse terms permit commercial
reuse with attribution unless the particular resource specifies
different terms. Special scientific-use/detailed microdata access has
distinct contractual restrictions. INE requires proper primary-source
attribution and makes the derived statistician responsible for the
precision of their own calculations.

## Inspection — without downloading from a GitHub runner

Download the official 2022 microdata ZIP using your **own browser**;
INE remote servers can time out when accessed from GitHub. Do NOT
commit the raw respondent file to the public repository or upload
its individual records into the API.

From the repo root, with existing `requirements.txt` installed:

```bash
python -m scripts.inspect_es_earnings_2022 --zip "C:/path/official-ees-2022.zip" > es-ees2022-inspection.json
```

Windows example:

```powershell
py -m pip install -r requirements.txt
py -m scripts.inspect_es_earnings_2022 --zip "C:\\Users\\USER\\Downloads\\official-ees-2022.zip" > es-ees2022-inspection.json
```

Only the **inspection JSON** (not row-level microdata) should be shared
for review. The full official package has already been checked; this is
retained for reproducibility and any future revised datasets. The inspector outputs archive filenames, variable
dictionary matches, source column headings, salary/occupation/
weight candidates, and a capped sample of categorical occupation
codes. It does not print individual salary values or create a wage
snapshot or SQLite database. For a standalone official CSV, use
`--csv FILE`. If a ZIP contains a second ZIP, the tool lists it
under `nested_archives`: unpack that official inner ZIP separately
and rerun the same inspector. TXT may be fixed-width and then must be
interpreted using the source-provided dictionary, not guessed.

## Approval gate — next phase only if confirmed by real dictionary

- Check whether actual CNO-11 codes are **four digit groups** (e.g.
  no generic `CNO1` source used as if it were a CNO4 classification).
- Independently approve full CNO11 code and **original category label**
  for each EarnWage occupation; ambiguous single subclasses cannot be
  relabelled as all doctors, nurses, or psychologists.
- Identify annual **gross earnings** variable (not net, not just
  October base pay), the proper supplied expansion/sample weight and
  eligible full-time/part-time selection rules.
- Calculate source-faithful weighted means and counts, use sensible
  minimum sample reliability thresholds and suppress sparse cells.
  Compare weighted all-employees earnings to published official 2022
  headline EUR 26,948.87 before trusting subgroup estimates.
- Keep Spain national geography separate from the Comunidad de Madrid,
  statutory public-sector scales, and hospital-sector wages. Record
  reference year 2022 and the particular survey universe.
- Source attribution: *Elaboração própria com microdados do INE,
  Encuesta de Estructura Salarial 2022 (www.ine.es)*, plus computation
  methodology. The original source does not validate our derived
  occupational outputs.
- Only **validated derived aggregate wage observations** (never
  individual records) would enter the future EarnWage SQLite snapshot.

**Exact occupation salary count from Spanish microdata: zero.** The
independent source-backed INE EAES 2008–2024 GROUP context snapshot is
already committed separately as `data/es_ine_eaes_28186.json`.
