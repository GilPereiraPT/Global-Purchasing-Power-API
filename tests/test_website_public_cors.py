"""Browser read-only CORS must not weaken EarnWage administrative endpoints."""
from fastapi.testclient import TestClient

from app.web_cors import allowed_public_origin, LEGACY_ORIGIN
from app.main import app
from app import native_wsgi

PREVIEW = "https://earnwage-preview.pages.dev"


def test_public_origin_exact_allowlist(monkeypatch):
    monkeypatch.setenv("EARNWAGE_PUBLIC_CORS_ORIGINS", PREVIEW + ", https://other.pages.dev")
    assert allowed_public_origin(LEGACY_ORIGIN)
    assert allowed_public_origin(PREVIEW)
    assert allowed_public_origin("https://other.pages.dev")
    for origin in (
        "https://evil.pages.dev",
        "https://earnwage-preview.pages.dev.evil.com",
        "http://earnwage-preview.pages.dev",
        "https://*.pages.dev",
        PREVIEW + "/",
        PREVIEW + "/anything",
        "null", None, "", "https://user@earnwage-preview.pages.dev",
    ):
        assert not allowed_public_origin(origin)


def test_fastapi_public_get_has_cors_but_admin_does_not(monkeypatch):
    monkeypatch.setenv("EARNWAGE_PUBLIC_CORS_ORIGINS", PREVIEW)
    client = TestClient(app)
    public = client.get("/v1/languages", headers={"Origin": PREVIEW})
    assert public.status_code == 200
    assert public.headers["access-control-allow-origin"] == PREVIEW
    evil = client.get("/v1/languages", headers={"Origin": "https://evil.pages.dev"})
    assert "access-control-allow-origin" not in evil.headers
    admin = client.get("/v1/admin/data-manager/status", headers={"Origin": PREVIEW})
    assert "access-control-allow-origin" not in admin.headers


def test_native_wsgi_public_get_cors_and_admin_preflight_stays_restricted(monkeypatch):
    monkeypatch.setenv("EARNWAGE_PUBLIC_CORS_ORIGINS", PREVIEW)
    monkeypatch.setattr(native_wsgi, "initialize", lambda: None)

    def call(path, method, origin):
        result = {}
        def start(status, headers):
            result["status"] = status
            result["headers"] = {name.lower(): value for name, value in headers}
        native_wsgi.application(
            {"REQUEST_METHOD": method, "PATH_INFO": path,
             "QUERY_STRING": "", "HTTP_ORIGIN": origin}, start)
        return result

    public = call("/v1/countries", "GET", PREVIEW)
    assert public["status"].startswith("200")
    assert public["headers"]["access-control-allow-origin"] == PREVIEW
    evil = call("/v1/countries", "GET", "https://evil.pages.dev")
    assert "access-control-allow-origin" not in evil["headers"]
    denied = call("/v1/admin/data-manager/status", "OPTIONS", PREVIEW)
    assert denied["status"].startswith("403")
    assert "access-control-allow-origin" not in denied["headers"]
    legacy = call("/v1/admin/data-manager/status", "OPTIONS", LEGACY_ORIGIN)
    assert legacy["status"].startswith("204")
    assert legacy["headers"]["access-control-allow-origin"] == LEGACY_ORIGIN
