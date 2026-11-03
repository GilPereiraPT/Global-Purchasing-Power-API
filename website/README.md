# EarnWage public website (first functional foundation)

This directory is a **separate public website**, not a replacement for the existing technical `docs/index.html` API Lab.

## Standalone comparison page (new)

- `compare.html` is the dedicated comparison experience, linked from the homepage and the country/occupation explorers.
- `compare.js` uses the existing API to populate the 14-country selector, occupation labels, available optional regions, and tax-model scenario metadata.
- Accepts origin annual gross salary and an optional destination annual offer. Fields use country currencies and a clearly marked annual period.
- A gross PPP equivalence is shown **only when** the API returns an available source-backed value. It does not convert or infer missing PPP.
- Tax scenario controls are **explicit opt-in**; the interface distinguishes verified and benchmark net outcomes from partial or unavailable results. Supported tax years/regions are sourced from the adapter metadata.
- Results use accessible tab buttons for purchasing power, tax outcomes and sources/methodology.
- All comparison headings and messages have seven-language translations in `compare-i18n.js`, with the same saved-language convention as other pages.
- The current backend API requires an occupation, even when the user supplies a salary. Changing that requirement remains a separate backend task.
- `gross_purchasing_power_equivalence` and `net_purchasing_power` depend on the not-yet-merged backend PRs #47 and #48. The page displays missing data honestly until deployed.
- **QA still needed:** real desktop/mobile browser tests, keyboard/screen-reader tests, tax-scenario edge cases, and live API/CORS validation. No rollout to production has been made.

## About EarnWage and user feedback

- `website/about.html` explains the mission, public statistical data sources, internal processing, missing-value policy and the important distinction between official statistics and third-party job listings.
- The About page includes a seven-language feedback form for incorrect values, translations, broken sources and suggestions, with consent and a supporting-source URL.
- `website/about.js` loads the consent-protected form and invokes `POST /api/report` on **Cloudflare Pages Functions**. The function lives at repository root `functions/api/report.js`; it is **not part of the Python API**.
- This form intentionally **remains disabled** until spam protection and email delivery are configured; it must not claim success unless Resend accepts the message. A project support email has **not** been invented or published.

### Configure the Cloudflare Pages reporting service

1. Create/verify a sender domain and address in Resend (or adapt the function for the chosen email provider).
2. Configure the following server-side environment variables for the Pages project: `REPORT_TO_EMAIL` (the private Gmail inbox selected by the project owner), `REPORT_FROM_EMAIL`, `RESEND_API_KEY`, `TURNSTILE_SECRET_KEY` and `REPORT_ALLOWED_ORIGIN` (the **exact** website origin, e.g. `https://example.org`). Do not commit the recipient email to this public repository. All feedback subjects follow `EarnWage: <category>` (Incorrect value / Translation issue / Source or broken link / Suggestion), with the visitor's email in Reply-To.
3. Create a Cloudflare Turnstile widget for the public site's hostname. Put **only its public site key** in `website/report-config.js`; keep the secret key in Cloudflare Pages secrets.
4. Add a Cloudflare WAF / rate-limit rule for `/api/report`; Turnstile and a honeypot are supplemental defences, not a rate limiter.
5. Test valid delivery, invalid captcha, invalid origin, oversized payload, errors from the mail provider and a mobile-browser submission before publishing.
6. Add a complete privacy notice explaining feedback retention and the mail service used. Do not request personal tax identifiers, documents, payslips or other sensitive information via this form.

The static website and Pages Function use the same domain, so the form needs no cross-origin access. Cloudflare Pages' build output stays `website`, with the `functions/` directory at repository root.

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
- The website includes 7 interface languages (`en`, `pt-PT`, `es`, `de`, `fr`, `it`, `nl`), selected at the top-right using flags and ISO language initials. Choice persists locally. Translations require a final native-speaker editorial review before public launch.
- This foundation does not yet have full on-site job-feed cards, region-aware tax scenario controls, charts, source explorer, or a downloadable Android release.
- No automated HTML/JavaScript browser tests or accessibility audit have been run in this session.

## Suggested next website work packages

1. Complete native-speaker language proofing, responsive and accessibility checks for the seven-locale header selector.
2. Make salary-only comparison independent from occupation in FastAPI and native WSGI.
3. Add a dedicated results page with gross PPP, independently sourced FX, region-aware fiscal scenarios and explicit availability states.
4. Build country/occupation discovery and salary history from existing sourced endpoints, respecting exact occupation versus major-group distinctions.
5. Add actual provider-authorised vacancy cards and a guided offer-to-comparison flow.
6. Add methodology, data-source pages, privacy, SEO and cookie handling (only if relevant services are introduced).
7. Validate responsive behaviour, keyboard/screen-reader access, build and e2e tests; then choose a domain and publish.

All changes should remain isolated until reviewed. No production databases, cron jobs, API routes or current Android app are changed by this branch.
