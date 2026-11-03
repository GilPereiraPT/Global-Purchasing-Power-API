# EarnWage public website (first functional foundation)

## Publicação atual: GitHub Pages

**Opção escolhida:** GitHub Pages, sem Cloudflare Pages neste momento.
O workflow `.github/workflows/earnwage-lab-pages.yml` prepara os ficheiros
`website/` como **raiz** do site estático e preserva o antigo laboratório
`docs/` na subpasta `/lab/`. A infraestrutura Python/cPanel da API não muda.

O endereço previsto é
`https://gilpereirapt.github.io/Global-Purchasing-Power-API/`;
a publicação só ocorrerá depois do merge do workflow e dos perfis na
branch `main` e de um deploy bem-sucedido, não pela abertura desta PR.

O GitHub Pages não suporta o endpoint `POST /api/report` do formulário
de feedback: esse formulário mantém-se desativado. Não há integração
com Cloudflare Pages/Functions, nem alteração de DNS.

Para os passos de verificação consulte
`website/PREVIEW_CHECKLIST.md`.


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

### Future option only: configure an external server-side reporting service

1. Create/verify a sender domain and address in Resend (or adapt the function for the chosen email provider).
2. Configure the following server-side environment variables for the Pages project: `REPORT_TO_EMAIL` (the private Gmail inbox selected by the project owner), `REPORT_FROM_EMAIL`, `RESEND_API_KEY`, `TURNSTILE_SECRET_KEY` and `REPORT_ALLOWED_ORIGIN` (the **exact** website origin, e.g. `https://example.org`). Do not commit the recipient email to this public repository. All feedback subjects follow `EarnWage: <category>` (Incorrect value / Translation issue / Source or broken link / Suggestion), with the visitor's email in Reply-To.
3. Create a Cloudflare Turnstile widget for the public site's hostname. Put **only its public site key** in `website/report-config.js`; keep the secret key in Cloudflare Pages secrets.
4. Add a Cloudflare WAF / rate-limit rule for `/api/report`; Turnstile and a honeypot are supplemental defences, not a rate limiter.
5. Test valid delivery, invalid captcha, invalid origin, oversized payload, errors from the mail provider and a mobile-browser submission before publishing.
6. Add a complete privacy notice explaining feedback retention and the mail service used. Do not request personal tax identifiers, documents, payslips or other sensitive information via this form.

This optional server-side integration is **not used on GitHub Pages**. The form is disabled until a separate verified backend and privacy notice are provided.

## Methodology, data sources and individual profile pages

- `methodology.html`: explains statistical measures, matching-year private-consumption PPP, tax verification, estimated versus missing values, and corrections.
- `sources.html`: retrieves inflation and private-consumption PPP for a selected country, retaining status, year, unit and original official source links.
- `country.html?country=PT`: country profile with currency, capital and available economic observations. Includes links to Compare and the occupation profile.
- `occupation.html?country=PT&occupation=accountant`: uses `/v1/earnwage/overview` to display exact occupation wages and annual presentation only when available, with broad group context explicitly separate.
- Shared `details.js` and `details-i18n.js` use the same seven-language selector and API as existing pages; no fictitious data or local wage database.
- `tests/test_website_details.py` checks page contracts, language completeness and missing-data policies.

These pages are available in the website branch only. **They have not been reviewed in a real browser or deployed.** Historical charts and a richer source catalog remain future work.

## Historical indicators and data coverage

- `history.html?country=PT&indicator=inflation_annual`: renders accessible SVG time series for official imported inflation or household-consumption PPP. Only actual dated observations are plotted; gaps are not interpolated. A sourced data table accompanies each chart.
- `coverage.html`: shows indicator availability for the 14 configured countries with latest observation year, plus links to country details/history.
- New read-only API `GET /v1/economy/history/{country}?indicator=inflation_annual|ppp_private_consumption`: uses existing `read_indicator(..., history=True)`, returns source/year/unit and stored history; performs no external fetch or production write. The same route is implemented in **both FastAPI and `app/native_wsgi.py`** for the existing Passenger/cPanel deployment.
- `history-i18n.js` localizes the two pages for EN/PT-PT/ES/DE/FR/IT/NL, consistent with browser language and locally saved choice.
- `tests/test_website_history.py` covers endpoint validation, preservation of missing historical years and page/i18n wiring.
- **Deployment dependency:** until the API endpoint is reviewed and deployed, the charts will display an unavailable state. Stored historical data must exist for each country/indicator.
- These are economic indicators only. Do not treat them as verified historical salary series or complete country coverage.

## Occupational-group earnings and source directory

- `wage-groups.html` — official published earnings by **broad occupational group**, using existing API routes for Portugal (INE/GEP Quadros de Pessoal), Spain (INE Encuesta Anual de Estructura Salarial) and Pakistan (Pakistan Bureau of Statistics Labour Force Survey). Group averages must not be substituted for any one profession's salary.
- Spain's EAES annual observations are charted **only when** at least two real annual years exist. Suppressed observations are shown as missing; short-sample quality flags are preserved in the table.
- Portugal's current official-group snapshot contains **2024 only**, so the page expressly says there is insufficient history for a trend. Pakistan periods **2020–21** and **2024–25** are published interval labels, not single calendar years; their original monthly observations are displayed without falsely connecting them in an annual chart.
- All country/source monetary units, periods, sex breakdowns, original source URLs and data limitations are retained. No invented salary interpolation, tax treatment or annualization.
- `source-directory.html` lists `/v1/sources` entries and their **actual published implementation status**. It explicitly separates official salary/statistics providers from independent third-party job listings and planned sources, without calling all records official.
- Shared `wage-library.js` and `wage-library-i18n.js` localize the pages in seven languages and use the live EarnWage API rather than duplicated site data. Static/regression tests are in `tests/test_website_wage_library.py`.
- Pages are in the pull-request branch only. Test browser behavior and existing API CORS configuration before deployment.

## Consolidação visual e pré-visualização

- `site-shell.js` + `site-shell.css`: navegação superior unificada e rodapé partilhado em todas as **15 páginas HTML**, incluindo menu secundário `Mais`, página ativa, traduções EN/PT-PT/ES/DE/FR/IT/NL e navegação por teclado. O ecrã móvel mantém o seletor de idioma e os links acessíveis.
- A preferência do idioma (`earnwage_lang`) é preservada; na primeira visita aplica-se o idioma do navegador se suportado, senão inglês.
- `api-config.js` contém o **único endereço público da API** utilizado pelos módulos de dados; não contém credenciais.
- `website/_headers` prepara respostas estáticas com `nosniff`, proteção de enquadramento e política de referenciação.
- `tests/test_website_shell.py`, `tests/test_website_api_config.py` e `tests/test_website_public_cors.py` acrescentam verificações automáticas de navegação, configuração e acesso seguro.
- **CORS:** a API da branch aceita origens adicionais configuradas em `EARNWAGE_PUBLIC_CORS_ORIGINS` (origens HTTPS completas, separadas por vírgulas) apenas em pedidos `GET/HEAD` públicos; rotas administrativas mantêm a autorização anterior. O novo código só produzirá efeitos quando for revisto e instalado no servidor.
- Antes de publicar no GitHub Pages, seguir `website/PREVIEW_CHECKLIST.md` (workflow de GitHub Actions, website na raiz, API Lab em `/lab/`, verificação de CORS e testes visuais).
- **Ainda não há deployment, publicação do site, alterações DNS ou alteração à BD de produção.** Testes visuais em browsers reais ainda pendentes.

## Current functionality

- Responsive editorial landing page with six capability cards, methodology and FAQ.
- Annual gross salary input, origin and destination selectors, country currency.
- Uses the existing `/v1/earnwage/compare` endpoint (occupation currently required by that API, so the site provides an optional-context selector and a safe default).
- Presents the gross national private-consumption PPP equivalence **only if** the backend responds with `gross_purchasing_power_equivalence.status=available`.
- Does not invent take-home salary; reports that an explicit tax scenario is required.
- Country and occupation selectors load from the existing API; country fallback is informational only.
- Job search opens the selected Indeed national website in a separate tab. No Indeed scraping.
- External Remotive link; no third-party listings copied into the website.

## Deployment (proposed): GitHub Pages

- GitHub repository: `GilPereiraPT/Global-Purchasing-Power-API`.
- Publish source: **GitHub Actions** on `main`, after explicit review/merge.
- Workflow: `.github/workflows/earnwage-lab-pages.yml`.
- Build output: `_site/`, assembled from `website/` at the root and `docs/` under `/lab/`.
- Public hosting: `https://gilpereirapt.github.io/Global-Purchasing-Power-API/` (subject to successful deployment).
- No external web host, custom domain, DNS or Cloudflare Pages configured now.

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
