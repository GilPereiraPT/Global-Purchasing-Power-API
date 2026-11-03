"""Ensure website API configuration and preview security stay centralized."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"website"
PAGES=(
    "index","compare","salaries","countries","jobs","insights","about",
    "methodology","sources","country","occupation","history","coverage",
    "wage-groups","source-directory",
)


def test_api_configuration_is_shared_and_loaded_before_other_scripts():
    config=(SITE/"api-config.js").read_text(encoding="utf-8")
    assert "https://earnwage-api.policlinicosdesantoandre.com" in config
    for name in PAGES:
        html=(SITE/(name+".html")).read_text(encoding="utf-8")
        assert 'src="./api-config.js"' in html
        assert html.index("api-config.js") < html.index("site-shell.js")
    for name in ("compare","explore","details","history","wage-library"):
        js=(SITE/(name+".js")).read_text(encoding="utf-8")
        assert "window.EarnWageConfig.apiBase" in js
        assert "https://earnwage-api.policlinicosdesantoandre.com" not in js
    index=(SITE/"index.html").read_text(encoding="utf-8")
    assert "const API=window.EarnWageConfig.apiBase;" in index


def test_preview_is_documented_without_auto_deploy():
    doc=(SITE/"PREVIEW_CHECKLIST.md").read_text(encoding="utf-8")
    for key in ("EARNWAGE_PUBLIC_CORS_ORIGINS", "REPORT_TO_EMAIL",
                "TURNSTILE_SECRET_KEY", "REPORT_ALLOWED_ORIGIN",
                "website/api-config.js", "Cloudflare Pages"):
        assert key in doc
    assert "Não executar deploy nem merge sem autorização" in doc


def test_static_security_headers_are_present():
    lines=(SITE/"_headers").read_text(encoding="utf-8")
    for header in ("X-Content-Type-Options: nosniff",
                   "Referrer-Policy: strict-origin-when-cross-origin",
                   "Permissions-Policy:", "X-Frame-Options: DENY"):
        assert header in lines
