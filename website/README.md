# EarnWage public website (first functional foundation)

This directory is a **separate public website**, not a replacement for the existing technical `docs/index.html` API Lab.

## Current functionality

- Responsive editorial landing page with six capability cards, methodology and FAQ.
- Annual gross salary input, origin and destination selectors, country currency.
- Uses the existing `/v1/earnwage/compare` endpoint (occupation currently required by that API, so the site provides an optional-context selector and a safe default).
- Presents the gross national private-consumption PPP equivalence **only if** the backend responds with `gross_purchasing_power_equivalence.status=available`.
- Does not invent take-home salary; reports that an explicit tax scenario is required.
- Country and occupation selectors load from the existing API; country fallback is informational only.
- Job search opens the selected Indeed national website in a separate tab. No Indeed scraping.
- External Remotive link; no third-party listings copied into the website.

## Deployment (proposed)

Cloudflare Pages can serve this directory as a static site:

- GitHub repository: `GilPereiraPT/Global-Purchasing-Power-API`
- Production branch: **only after an explicitly approved merge**
- Framework preset: None
- Build command: empty
- Build output directory: `website`
- Environment variables: none are required by this static version
- Add the custom domain and DNS **only after choosing the actual domain** and reviewing access.

The existing cPanel/Passenger Python API remains independent; do not move or redeploy it as part of the website work. The frontend currently calls `https://earnwage-api.policlinicosdesantoandre.com`; verify its CORS allow-list for the **chosen** public website origin before deployment. Do not use a wildcard CORS policy for authenticated administrative endpoints.

## Honest limitations

- The gross PPP function is implemented in the separate PR #47, and net-PPP gating in #48. Until those changes are approved and deployed to the API, the website may show PPP as unavailable.
- The API currently requires an occupation for its comparison endpoint. Make salary-only comparison truly occupation-independent in a later backend PR.
- The website currently starts in English. Locale content for `pt`, `es`, `de`, `fr`, `it`, `nl` requires an audited i18n pass.
- This foundation does not yet have full on-site job-feed cards, region-aware tax scenario controls, charts, source explorer, or a downloadable Android release.
- No automated HTML/JavaScript browser tests or accessibility audit have been run in this session.

## Suggested next website work packages

1. Add multilingual, accessible navigation and content; Portuguese is PT-PT.
2. Make salary-only comparison independent from occupation in FastAPI and native WSGI.
3. Add a dedicated results page with gross PPP, independently sourced FX, region-aware fiscal scenarios and explicit availability states.
4. Build country/occupation discovery and salary history from existing sourced endpoints, respecting exact occupation versus major-group distinctions.
5. Add actual provider-authorised vacancy cards and a guided offer-to-comparison flow.
6. Add methodology, data-source pages, privacy, SEO and cookie handling (only if relevant services are introduced).
7. Validate responsive behaviour, keyboard/screen-reader access, build and e2e tests; then choose a domain and publish.

All changes should remain isolated until reviewed. No production databases, cron jobs, API routes or current Android app are changed by this branch.
