"""Strict browser origin allow-list for read-only public EarnWage API routes.

The legacy GitHub Pages origin remains supported. Additional website origins are
explicitly configured as comma-separated full HTTPS origins; wildcards are refused.
This function does not confer authorization to /v1/admin endpoints.
"""
import os
from urllib.parse import urlsplit

LEGACY_ORIGIN = "https://gilpereirapt.github.io"


def _exact_https_origin(value: str) -> bool:
    if not isinstance(value, str) or not value or len(value) > 253 or "*" in value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (parsed.scheme == "https" and bool(parsed.hostname) and
            parsed.netloc == parsed.hostname and not parsed.path and
            not parsed.query and not parsed.fragment and not parsed.username and
            not parsed.password)


def allowed_public_origin(value: str | None) -> bool:
    if value == LEGACY_ORIGIN:
        return True
    if not value or not _exact_https_origin(value):
        return False
    origins = os.environ.get("EARNWAGE_PUBLIC_CORS_ORIGINS", "")
    return any(value == item.strip() and _exact_https_origin(item.strip())
               for item in origins.split(",") if item.strip())
