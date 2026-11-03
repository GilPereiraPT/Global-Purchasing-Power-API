# EarnWage country guides · ES, IE, GB, FR, NL, CH

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

Source links are embedded in the country metadata. The **Switzerland** reference snapshot
is currently kept in private staging pending licensing/reuse and quality review. This
website code does not import, disclose, publish or manufacture that dataset.

All changes in PR #51 are staged on top of the previous PR for ES/IE/GB, which itself
depends on the new website PR #49. They require CI and browser checks, and must not
be deployed or merged into production without review.
