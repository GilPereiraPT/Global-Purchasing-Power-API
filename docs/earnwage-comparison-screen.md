# EarnWage — mobile comparison screen contract (next iteration)

This specification describes the first Android/web comparison screen against the existing v0.5.3 API. It is a UI contract, not a claim that cost-of-living or net-pay computation exists.

## Flow

1. Fetch `GET /v1/app-config` for brand, supported countries and languages; fetch occupation catalogue from `GET /v1/occupations?lang=pt` (English fallback for untranslated languages).
2. User chooses origin and destination countries, a profession, and optionally a region (only if the chosen country exposes a region selector). A selected US state or Canadian province must never imply state/provincial income tax is calculated.
3. User may enter a separate **annual gross salary** for each side, with the country currency shown next to the input. Never pre-fill the personal salary from a statistical occupation wage. Require positive finite numbers, and keep annual vs hourly units explicit.
4. Request `GET /v1/earnwage/compare` with `country_a`, `country_b`, `occupation`, optional `region_a`, `region_b`, and optional per-country annual-gross fields as supported by the API schema. Omit unset optional parameters. Confirm parameter names against the API before wiring the client.
5. Show two country cards with source-linked official occupation wage, original unit, statistic (mean/median), observation period, optional partial tax components, and limitations. For missing values show “Data not available”, not zero or an inferred figure.
6. Display no cross-country salary winner, net-pay number, purchasing-power score, capital-city spending estimate, or automatic currency/unit conversion until each required data source and calculation has been implemented and tested.

## Empty, loading and error states

- Initial: prompt for countries and occupation.
- Loading: disable repeated comparison submissions, preserve selections.
- Missing official observation: explain that this profession/country combination is not yet covered and permit entering an independent salary scenario.
- Partial tax result: label “Partial deductions only — not net salary”; list exclusions supplied by the API.
- Network failure: preserve inputs and offer retry; do not substitute sample numbers in production.

## Acceptance tests

- US and CA selections expose conditional region selectors; Portugal does not.
- Canada Québec never inherits non-Québec tax assumptions.
- Different salary units and currencies remain visible, with no unsupported numeric comparison.
- Missing wage or expenses render explicit unavailable states.
- Every sourced value displays its reference period and provider attribution.
- The comparison screen remains usable even when only one country has an official occupation wage.

## Next backend milestones

1. Verify the production native WSGI health and consolidated endpoints after deployment; local tests do not prove live hosting.
2. Increase validated wage coverage without interpolating occupations or silently mapping incompatible job classifications.
3. Add country-specific validated tax engines and explicit user circumstances before presenting net pay.
4. Add geographically compatible cost-of-living baskets and exchange-rate reference dates before computing purchasing-power comparisons.
