"""No HTTP server or ASGI bridge needed to test Passenger WSGI entry."""
import io
import json
from urllib.parse import urlencode

from app.native_wsgi import application


def request(path, params=None, method="GET"):
    status = []
    headers = []
    environ = {"PATH_INFO": path, "REQUEST_METHOD": method,
               "QUERY_STRING": urlencode(params or {}),
               "wsgi.input": io.BytesIO(b"")}
    def start_response(code, response_headers):
        status.append(code)
        headers.extend(response_headers)
    chunks = application(environ, start_response)
    raw = b"".join(chunks)
    return int(status[0].split()[0]), json.loads(raw) if raw else None, dict(headers)


def test_native_wsgi_health_and_config():
    from passenger_wsgi import application as passenger_application
    assert passenger_application is application
    code, body, headers = request("/v1/health")
    assert code == 200
    assert body["status"] == "ok"
    assert body["version"] == "0.5.8"
    assert body["runtime"] == "native_wsgi"
    assert headers["Content-Type"].startswith("application/json")
    assert request("/v1/app-config")[1]["product"]["name"] == "EarnWage"
    assert request("/v1/countries")[1]["count"] == 14
    assert len(request("/v1/occupations", {"lang": "pt"})[1]["occupations"]) == 40
    assert len(request("/v1/regions/US")[1]["options"]) == 50
    assert len(request("/v1/regions/CA")[1]["options"]) == 13
    assert request("/v1/regions/PT")[1]["visible"] is False
    assert request("/v1/regions/XX")[0] == 404


def test_native_wsgi_official_wages_and_comparison():
    status, data, _ = request("/v1/earnwage/coverage")
    assert status == 200 and data["possible_pairs"] == 560
    assert data["observed_pairs"] == 38
    code, wage, _ = request("/v1/salaries/US/nurse")
    assert code == 200 and wage["status"] == "available"
    assert wage["observations"][0]["unit"] == "USD/year"
    code, item, _ = request("/v1/earnwage/overview", {
        "country": "CA", "occupation": "nurse", "region": "ON"})
    assert code == 200
    assert item["national_occupation_wage"]["observations"][0]["unit"] == "CAD/hour"
    assert item["tax_scenario"]["status"] == "not_requested"
    code, comp, _ = request("/v1/earnwage/compare", {
        "country_a": "US", "country_b": "CA", "occupation": "nurse"})
    assert code == 200
    assert comp["net_purchasing_power"]["value"] is None
    assert comp["wage_comparability"]["status"] == "not_normalized"


def test_native_wsgi_partial_fiscal_and_errors():
    code, tax, _ = request("/v1/tax-components/US", {"annual_gross": "101420"})
    assert code == 200 and tax["net_income"] is None
    code, tax, _ = request("/v1/earnwage/overview", {
        "country": "CA", "region": "QC", "occupation": "nurse",
        "annual_gross": "100000"})
    assert code == 200 and tax["tax_scenario"]["status"] == "unavailable"
    assert request("/v1/earnwage/overview", {
        "country": "US", "occupation": "nurse", "region": "QC"})[0] == 422
    assert request("/v1/health", method="POST")[0] == 405
    assert request("/v1/tax-components/US")[0] == 422
    assert request("/v1/health", {"a": "1"}, method="HEAD")[1] is None
    assert request("/v1/no-such-route")[0] == 404
