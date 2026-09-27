# EarnWage: verified salaries by specific occupation — Portugal first

## Confirmed problem

For PT, the 2026-09-27 inventory has **0/40 exact occupation salary pairs**.
The source-backed ILOSTAT major-group dataset is independent, and its large
ISCO-08 group 2 includes doctors, nurses and psychologists (among many other
professionals). Reusing the same group mean under each occupation misleads
users even when small-print warns them.

The API guardrail now makes `annual_presentation` unavailable when no
verified exact occupation wage exists. The broad ILOSTAT mean remains available
only in `national_major_group_context` / the separate groups endpoint.
The Android wage card shows 'occupation-specific wage unavailable', not an
identical annualized group amount. No production wage database has been
rewritten; API and Android builds must be deployed separately.

## Source candidates — national statistical wages vs public pay scales

1. **INE / GEP Quadros de Pessoal**, gain by region and occupation CPP:
   https://www.ine.pt/xurl/indx/0010385/PT
   Open data record:
   https://dados.gov.pt/pt/datasets/ganho-medio-mensal-eur-7
   INE JSON:
   https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0010385&lang=PT
   Metadata:
   https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp?varcd=0010385&lang=PT
   Dataset record lists CC BY 4.0. **Before ingestion inspect the returned
   occupation classification/granularity.** A CPP code for 'health
   professionals' / ISCO group 22 or 'specialists' / group 2 must NOT be
   mapped to doctor or nurse. Import exact CPP codes only when the source's
   category unambiguously matches the curated job, or label a narrower
   subgroup explicitly. Statistics normally cover employees under the
   Quadros de Pessoal universe; do not claim total public+private coverage.
2. GEP Quadros de Pessoal, 2024 publication and 2014–2024 historical series:
   https://www.gep.mtsss.gov.pt/
   The published salary measure may be *remuneração base* or *ganho*, which
   are different. Region, month/year and sampled universe must be retained.
   Available headline publication tables may use broad **two-digit CPP**
   groups and cannot independently solve exact profession pay.
3. **DGAEP SRAP 2026** (public-sector base pay by career, category, step,
   and working-time regime):
   https://www.dgaep.gov.pt/srap/index.htm
   These are statutory **pay scales**, NOT observed occupation mean salary,
   not private market rates, and not an unqualified salary for everyone.
   Nurses, medical career tracks, psychologist public-sector categories
   must stay distinct where official categories are verified. Check reuse
   terms before redistributing compiled values beyond linking.
4. Exact ILOSTAT ISCO-08 four-digit observations, if valid official data are
   downloaded and the local-currency/unit/source/year mapping passes
   `app/ilostat_import.py`. The major-group snapshot is not a substitute.

## Proposed data contract for a future verified PT occupation importer

Store and display one record for each explicit and verifiable combination:
country PT; occupation; source CPP/ISCO code; source and source URL;
period; scope (Continente/Portugal, public/private, employee universe);
salary concept (base/earnings/pay-scale); gross/net; EUR per month/year/hour;
statistic (mean/median/statutory rate); working time if stated; collected
geography; sample/coverage and licence. Never invent 14 annual payments
from a reported monthly observation; annualized × 12 must be labelled as
a comparison equivalent, not statutory annual earnings.

Sample UI:
- Doctor — average monthly gain [only once validated at doctor CPP level];
  otherwise 'No verified occupation wage'.
- Nurse — own professional mean [only if independently sourced].
- Psychologist — own professional mean [only if independently sourced].
- Group 2 ILOSTAT — a separate OPTIONAL context panel titled 'All specialists;
  not the selected occupation' and excluded from pay comparisons.

No source data have been imported or guessed in this fix. Validate INE source
schema and actual category coverage before designing importer or claiming a
40/40 Portuguese salary series.
