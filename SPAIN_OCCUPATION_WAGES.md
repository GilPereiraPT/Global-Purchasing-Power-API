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
published 23 September 2024, supplies **free anonymised microdata**:
from the official results page select **Microdatos → Año 2022 →
Ficheros de Microdatos**. The package includes CSV/TXT variants and a
variable-dictionary/design file. This source contains employee records;
it is NOT a ready-made 4-digit occupation wage table. Whether the free
anonymised data contain CNO-11 4-digit detail remains unverified until
the actual archive and dictionary are inspected.

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
for review. The inspector outputs archive filenames, variable
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

**Current production count for this new Spanish source: zero.** This
PR is schema investigation tooling, not a verified salary import.
