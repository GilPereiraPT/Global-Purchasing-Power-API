from fastapi.testclient import TestClient
from app.catalog import OCCUPATIONS, SUPPORTED_LANGUAGES
from app.main import app


def test_every_job_has_each_supported_translation():
    assert len(OCCUPATIONS) == 40
    for job in OCCUPATIONS:
        assert set(job["translations"]) == set(SUPPORTED_LANGUAGES)
        assert all(job["translations"].values())


def test_localized_labels_and_stable_ids():
    with TestClient(app) as client:
        for lang, expected in [("pt", "Contabilista"), ("en", "Accountant"),
                               ("es", "Contable"), ("de", "Buchhalter/in"),
                               ("fr", "Comptable"), ("it", "Contabile"),
                               ("nl", "Accountant")]:
            response = client.get("/v1/occupations", params={"lang": lang})
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 40
            assert data["occupations"][0]["id"] == "accountant"
            assert data["occupations"][0]["label"] == expected


def test_search_accepts_aliases_accents_and_other_language():
    with TestClient(app) as client:
        for term in ["contabilidade", "accounting", "Buchhaltung", "comptabilité"]:
            result = client.get("/v1/occupations", params={"lang": "pt", "q": term}).json()
            assert any(job["id"] == "accountant" for job in result["occupations"])
        result = client.get("/v1/occupations", params={"lang": "pt", "q": "medico"}).json()
        assert any(job["id"] == "doctor" for job in result["occupations"])


def test_salary_matrix_has_localized_display_without_changing_ids():
    with TestClient(app) as client:
        data = client.get("/v1/salaries/availability/matrix?lang=pt").json()
        cell = next(x for x in data["cells"] if x["country"] == "PT" and x["occupation"] == "accountant")
        assert cell["occupation_label"] == "Contabilista"
        assert cell["occupation"] == "accountant"
        assert cell["status"] == "unavailable"


def test_missing_translation_falls_back_in_wsgi_and_asgi(monkeypatch):
    import app.native_wsgi as wsgi
    from app import main as asgi
    jobs = [dict(job) for job in OCCUPATIONS]
    jobs[0] = {**jobs[0], "translations": {
        key: value for key, value in jobs[0]["translations"].items() if key != "pt"
    }}
    monkeypatch.setattr(wsgi, "OCCUPATIONS", jobs)
    monkeypatch.setattr(asgi, "OCCUPATIONS", jobs)
    assert wsgi.dispatch("/v1/occupations", {"lang": ["pt"]})["occupations"][0]["label"] == "Accountant"
    assert wsgi.dispatch("/v1/salaries/availability/matrix", {"lang": ["pt"]})["cells"][0]["occupation_label"] == "Accountant"
    with TestClient(app) as client:
        result = client.get("/v1/occupations?lang=pt")
        assert result.status_code == 200
        assert result.json()["occupations"][0]["label"] == "Accountant"
        matrix = client.get("/v1/salaries/availability/matrix?lang=pt")
        assert matrix.status_code == 200
        assert matrix.json()["cells"][0]["occupation_label"] == "Accountant"
