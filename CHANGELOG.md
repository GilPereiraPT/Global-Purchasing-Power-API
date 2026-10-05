# Changelog

## Android 0.9.0 (build 6) — proposed

- User-entered annual gross salary comparison using national consumption PPP from World Bank WDI, at the latest common observation year.
- Partial results retain inflation context when comparable PPP is missing.
- OkHttp public GET requests with bounded retries, private device cache and explicitly dated offline results.
- Restore the last successful result on startup; disable Android backup for salary inputs stored on the device.
- Sources and attribution screen with visible links to World Bank, Eurostat, ECB, ILOSTAT, BLS, Canada Job Bank and Remotive.

## API 0.5.20 — salary-equivalence extension (proposed)

- `/v1/earnwage/equivalence` and `/v1/earnwage/equivalence/coverage`, shared by FastAPI and native WSGI.
- Gross approximation only; tax estimates and regional price levels are not inferred.
- HTTP cache defaults to the application's `var/` directory; `GPP_CACHE_DB` remains configurable.

## Android 0.8.0 (build 5)

- Optimized internal test APK, country indicators, occupational salary comparison and job search.
- Internal release uses a debug signing key; not a Play Store release.
