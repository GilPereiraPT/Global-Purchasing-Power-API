# EarnWage weather integration — MET Norway

This change adds a **model forecast**, not a live weather observation or a
climatological average, for the **capital only** of each of 14 countries.

## Why MET Norway?
- Locationforecast 2.0 covers the world and up to about 9 days of forecasts.
- MET Norway permits commercial reuse under **CC BY 4.0** with attribution.
- We use the EarnWage API as a caching proxy, not browser-to-MET calls.

Sources and licence:
- https://api.met.no/doc/TermsOfService
- https://api.met.no/weatherapi/locationforecast/2.0/documentation
- https://creativecommons.org/licenses/by/4.0/

## To enable on the existing Python / Passenger host
1. Review and deploy the same implementation in both `app/main.py` and
   `app/native_wsgi.py` after CI. Do not change the configured databases.
2. Set `EARNWAGE_WEATHER_CONTACT` as a **real contact** URL or email that
   MET Norway can use to reach the operator. Merely configuring a dummy value
   or unmaintained repository page is insufficient. Example syntax only:
   `EARNWAGE_WEATHER_CONTACT=https://example.com/contact`.
3. Restart the relevant application worker, then verify
   `GET /v1/weather/PT/0` and `GET /v1/weather/CA/0`.
4. Check upstream traffic, response Expires, location coordinates and source
   attribution. Run mock tests then browser/mobile tests. Production can
   remain on the previous release until approved.

With no real contact configured, the endpoint returns
`status: not_configured` without contacting the provider. With no approved
coordinate for the selected city, it returns `not_covered` — **never**
substitutes a different city's forecast. No API key is required.

MET cache responses are kept per city within each Python worker, at least one
hour or until upstream `Expires`, whichever is later. They are conditional
on `Last-Modified` during a refresh. Failed refreshes retain the cached
forecast but mark it stale. Shared cache across multiple Passenger workers is
a later operational optimisation; tune worker counts and request volume.

The capital coordinates are **approximate city centres**, specified to four
decimals. They are not location measurements. Weather grid forecasts can
differ from actual conditions, especially with altitude and coastal terrain.

## Explicitly not in scope
- No meteorological values for non-capital cities until verified coordinates
  are reviewed and integrated on both client and server.
- No monthly historical climate averages or weather station measurements.
- Daily low/high values are calculated from available predicted samples, not
  independently reported daily extremes; the first local day can be partial.
- No historical weather or time-series interpolation, no price or paid
  Open-Meteo subscriptions, no production deployment or database mutation.

The existing country selectors, time comparisons, demographic and political
profiles remain unchanged. The next weather iteration should extend coordinate
coverage to each existing city with geographic source references, then procure
historical reanalysis/climate normals under an independently verified licence.
