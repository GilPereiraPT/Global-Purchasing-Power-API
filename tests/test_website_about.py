"""Static safeguards for About EarnWage and feedback form."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"website"


def test_about_page_has_feedback_form_and_nav():
    html=(SITE/"about.html").read_text(encoding="utf-8")
    assert 'id="reportForm"' in html
    assert 'id="reportMessage"' in html
    assert 'id="reportEmail"' in html
    assert 'id="consent"' in html
    assert 'id="captchaContainer"' in html
    assert 'id="sendReport" disabled' in html
    for page in ("index","compare","salaries","countries","jobs","insights"):
        assert f'./{page}.html' in html


def test_about_translations_are_complete():
    raw=(SITE/"about-i18n.js").read_text(encoding="utf-8").strip()
    prefix="window.EarnWageAboutI18n="
    assert raw.startswith(prefix)
    catalogue=json.loads(raw.removeprefix(prefix).rstrip(";"))
    assert tuple(catalogue)==("en","pt","es","de","fr","it","nl")
    expected=set(catalogue["en"])
    for lang,data in catalogue.items():
        assert set(data)==expected
        assert all(isinstance(s,str) and s.strip() for s in data.values())


def test_report_endpoint_never_embeds_destination_or_api_key():
    source=(ROOT/"functions/api/report.js").read_text(encoding="utf-8")
    client=(SITE/"about.js").read_text(encoding="utf-8")
    assert "REPORT_TO_EMAIL" in source
    assert "REPORT_FROM_EMAIL" in source
    assert "RESEND_API_KEY" in source
    assert "TURNSTILE_SECRET_KEY" in source
    assert "REPORT_ALLOWED_ORIGIN" in source
    assert "challenges.cloudflare.com/turnstile/v0/siteverify" in source
    assert 'window.turnstile.getResponse' in client
    assert 'if(!/^[A-Za-z0-9_-]{12,128}$/.test(siteKey))' in client
    assert 'result.status!=="sent"' in client
    assert "RESEND_API_KEY" not in client
