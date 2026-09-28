# United Kingdom occupation wages — ONS ASHE 2025

## Source and release

EarnWage uses the Office for National Statistics (ONS) **Annual Survey of
Hours and Earnings (ASHE), Table 14 — Occupation (4-digit SOC)**, 2025
provisional release.

Official dataset:
https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/occupation4digitsoc2010ashetable14/2025provisional

The 2025 provisional release was published on 23 October 2025. ONS issued a
correction on 19 December 2025 affecting occupation 3312 (Police officers) in
some annual-pay tables. EarnWage downloads the corrected ZIP.

The committed aggregate snapshot is:
`data/uk_ashe_wages.json`

It is generated from:
- **Table 14.7a — Annual pay - Gross (£)**; and
- **Table 14.7b — coefficients of variation (CV) for the same estimates**.

No ASHE microdata or individual employee records are committed.

## Statistical measure

The source publishes both mean and median annual gross pay. EarnWage stores
both where ONS publishes a usable estimate, but uses **median as the preferred
display measure** for this source. ONS describes the median as its preferred
measure of average earnings because it is less affected by a small number of
very high earners.

No annual-to-contractual-monthly salary inference is made. If the client shows
an optional monthly comparison it is explicitly annual/12.

## Quality gate

For every mapped SOC 2020 unit group, EarnWage matches Table 14.7a to its
corresponding Table 14.7b CV cell:

- CV <= 5%: `precise`
- 5% < CV <= 10%: `reasonably_precise`
- 10% < CV <= 20%: `acceptable`
- CV > 20%, `x`, disclosure suppression, unavailable/non-applicable cells:
  **not imported**

The importer never converts an ONS suppression marker into a wage.

## EarnWage coverage in the validated 2025 snapshot

The snapshot currently contains **52 observations for 26 of the 40 EarnWage
occupations**: median and mean for each accepted occupation.

Accepted mappings:

| EarnWage | SOC 2020 | ONS title |
|---|---:|---|
| accountant | 2421 | Chartered and certified accountants |
| financial_analyst | 2422 | Finance and investment analysts and advisers |
| pharmacist | 2251 | Pharmacists |
| physiotherapist | 2221 | Physiotherapists |
| preschool_teacher | 2315 | Nursery education teaching professionals |
| software_developer | 2134 | Programmers and software development professionals |
| civil_engineer | 2121 | Civil engineers |
| mechanical_engineer | 2122 | Mechanical engineers |
| architect | 2451 | Architects |
| receptionist | 4216 | Receptionists |
| sales_assistant | 7111 | Sales and retail assistants |
| truck_driver | 8211 | Large goods vehicle drivers |
| bus_driver | 8212 | Bus and coach drivers |
| electrician | 5241 | Electricians and electrical fitters |
| plumber | 5315 | Plumbers & heating and ventilating installers and repairers |
| cook | 5435 | Cooks |
| waiter | 9264 | Waiters and waitresses |
| cleaner | 9223 | Cleaners and domestics |
| security_guard | 9231 | Security guards and related occupations |
| healthcare_assistant | 6131 | Nursing auxiliaries and assistants |
| data_analyst | 3544 | Data analysts |
| cybersecurity_specialist | 2135 | Cyber security professionals |
| secondary_teacher | 2313 | Secondary education teaching professionals |
| warehouse_operator | 9252 | Warehouse operatives |
| welder | 5213 | Welding trades |
| automotive_mechanic | 5231 | Vehicle technicians, mechanics and electricians |

The ASHE workbook writes SOC 5315 with `&`; the SOC classification page uses
`and`. The code and unit-group meaning are the same and EarnWage preserves
the exact ASHE source title in the snapshot.

**Dental practitioners (SOC 2253)** are a valid conceptual mapping for
EarnWage `dentist`, but both 2025 annual median and mean are suppressed /
fail the CV quality gate, so no dentist wage is imported.

## Deliberately not mapped

Generic EarnWage labels are not forced into one SOC 2020 unit group when the
source classification divides them into materially different occupations.
Examples include doctor (generalist vs specialist medical practitioners),
nurse (multiple nursing unit groups), psychologist, teacher, IT technician,
manager, construction worker and lawyer.

This is a deliberate data-quality rule. An exact-source gap is preferable to
showing a narrower subgroup as though it represented the full EarnWage title.

## Examples from the committed 2025 source

These are national annual gross medians, not London salaries and not job
offers:

- Software developer (SOC 2134): GBP 55,587; CV 3.0%
- Civil engineer (SOC 2121): GBP 50,602; CV 5.3%
- Pharmacist (SOC 2251): GBP 47,508; CV 5.8%
- Physiotherapist (SOC 2221): GBP 37,917; CV 3.7%
- Secondary teacher (SOC 2313): GBP 44,246; CV 1.6%
- Plumber (SOC 5315): GBP 36,563; CV 3.8%
- Accountant (SOC 2421): GBP 45,538; CV 5.8%

## API behaviour

On startup FastAPI and the native Passenger/WSGI worker load the committed
snapshot into the existing server SQLite cache database.

The standard endpoints therefore use ONS ASHE for accepted UK mappings:

`GET /v1/salaries/GB/{occupation}`

`GET /v1/earnwage/overview?country=GB&occupation={occupation}`

`GET /v1/earnwage/history?country=GB&occupation={occupation}&start_year=2025&end_year=2025`

`GET /v1/earnwage/coverage`

`GET /v1/data-inventory`

ASHE exact occupation data remain independent from ILOSTAT major-group
context.

## Reuse and attribution

ONS statistical content is reused under the Open Government Licence v3.0.
Suggested attribution:

> Source: Office for National Statistics, Annual Survey of Hours and Earnings
> (ASHE), Table 14, 2025 provisional. Processed by EarnWage.

EarnWage is not endorsed by ONS.
