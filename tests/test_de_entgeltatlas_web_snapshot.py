"""Ensure German public website only shows the approved exact-scope national BA data."""
import json
from pathlib import Path
from app.de_entgeltatlas_states import STATES
from app.de_entgeltatlas_wages import APPROVED

ROOT = Path(__file__).resolve().parents[1]


def test_public_german_website_matches_exact_national_entgeltatlas_snapshot():
    canonical = json.loads((ROOT / "data/de_entgeltatlas_wages.json").read_text(encoding="utf8"))
    public = json.loads((ROOT / "docs/data/de-entgeltatlas-2025.json").read_text(encoding="utf8"))
    records = [
        {"occupation": row["occupation"], "label": row["profession_title"],
         "occupational_aggregate": row["occupational_aggregate"],
         "value": row["value"], "period": row["reference_period"],
         "source_url": row["source_url"], "precision": row["precision"]}
        for row in canonical["records"]
    ]
    assert public["schema"] == 1
    assert public["records"] == records
    assert len(records) == 27 == len(APPROVED)
    assert len(STATES) == 16
    assert all(row["precision"] == "occupation_specific_kldb_berufsgattung_no_fallback"
               for row in records)


def test_germany_direct_page_and_selector_do_not_fabricate_state_mediana():
    index = (ROOT / "docs/index.html").read_text(encoding="utf8")
    page = (ROOT / "docs/germany.html").read_text(encoding="utf8")
    assert 'href="./germany.html?occupation=software_developer&region=BY"' in index
    assert 'fetch("./data/de-entgeltatlas-2025.json"' in page
    assert 'data.records.find(r=>r.occupation===job)' in page
    assert "Importação pendente" in page
    assert "não são tratados aqui como salário específico" in page
    assert "earnwage-api.policlinicosdesantoandre.com" not in page
