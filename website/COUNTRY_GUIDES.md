# EarnWage country guides · ES, IE, GB, FR, NL, CH, IT, US, CA

The website shares **one** country profile route, `website/country.html?country=XX`.
Sourced country detail is in `website/country-guides.js`; the country listing
`website/countries.html` links to each profile. Source values are fetched
from `/v1/earnwage/overview` only. All seven existing website languages have
guide notes and measure labels.

| Code | Source and reference | Displayed as | Distinctions |
| --- | --- | --- | --- |
| ES | INE EAES 28186, 2008–2024 | Broad CNO-11 groups only | Not an individual occupation wage; suppressed cells stay missing |
| IE | HSE and other public scales 2026; CSO SES 2022 | Public-sector career entry + separately identified hourly group context | Neither is a national private-sector profession average |
| GB | ONS ASHE 2025 (provisional) | Validated SOC 2020 occupation annual gross pay | Only source-backed observation, suppressed data excluded |
| FR | INSEE Base Tous salaires 2024 | National **mean net monthly** private-sector EQTP salaries by approved PCS-ESE | Do not label as gross or apply 2026 personal tax assumptions |
| NL | CBS 86355NED, 2024 definitive and 2025 provisional | **Median gross hourly** employee pay by approved BRC group | Do not annualise or assume individual occupation precision beyond BRC mapping |
| CH | Swiss FSO ESS CH-ISCO-19 sub-major groups | Group context only, and only if publicly approved data exist in API | Private staging is not published; do not substitute fabricated salary or claim profession precision |
| IT | Excelsior 2025 (INPS 2023); ISTAT SES 2022 | **Initial gross annual** RAL for selected professions; broad-group **gross hourly means by sex** separately | Ranges show min and max without invented midpoint; group means are not profession salaries |
| US | BLS OEWS May 2025 | National and validated state-wide occupation observations with source hourly/annual units | Region optional; no city substitution, no assumed net income, missing states unavailable |
| CA | Job Bank 2025 / NOC 2021 | National and validated provincial occupation observations with original hourly/annual units | Observation years vary, no annualisation of hourly wages, no complete federal/provincial income-tax model |

Source links are embedded in the country metadata. The **Switzerland** reference snapshot
is currently kept in private staging pending licensing/reuse and quality review. This
website code does not import, disclose, publish or manufacture that dataset.

All changes in PR #51 are staged on top of the previous PR for ES/IE/GB, which itself
depends on the new website PR #49. They require CI and browser checks, and must not
be deployed or merged into production without review.

## Third batch: Italy, US, Canada (PR #52)

- The Italy country profile uses `italy_cp2021_major_group_context` only
  for source-published **2022 group-level mean hourly earnings by sex**;
  profession-specific **2023 initial RAL** is shown separately. Published
  RAL intervals preserve both endpoints; no midpoint is inferred.
- United States and Canada now use the API's existing `region.ui.options`
  from `/v1/earnwage/overview`, so the optional geographic selector
  does **not** maintain a duplicate hardcoded list of states/provinces.
- A region selection sends `region=XX` to the API and reads only
  `regional_occupation_wage`; its absence stays explicitly unavailable.
  The national statistic remains displayed **separately**, without
  claiming that it applies to the state/province selected.
- The US regional result selects the source's **annual median** if
  available, else annual mean, then hourly median/mean, preserving units.
  Canada prefers the source's **median** with its native hourly/annual unit,
  otherwise the source's mean. Neither country uses regional tax
  assumptions to manufacture net salary.
- Reported source reference periods are retained. A release published in
  2025 does not mean that each Canadian occupation was surveyed in 2025.
- The three profiles and all measure descriptions exist in EN/PT/ES/DE/FR/IT/NL.
- No API/backend mutation, imports, database access, DNS change or production
  deployment. CI and real-browser review remain required.
