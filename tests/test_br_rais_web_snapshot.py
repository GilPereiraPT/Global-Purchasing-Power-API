"""Prevent Brazil wage drift between canonical RAIS snapshot and public web display."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_brazil_direct_lookup_agrees_with_verified_api_snapshot():
    raw = json.loads((ROOT / "data/br_rais_2025_states.json").read_text(encoding="utf8"))
    public = json.loads((ROOT / "docs/data/br-rais-2025-states.json").read_text(encoding="utf8"))
    expected = [[row["occupation"], row["uf"], row["value"], row["links"],
                 row["cbo_code"], row["source_url"]] for row in raw["records"]]
    assert public["schema"] == 1
    assert public["country"] == "BR"
    assert public["period"] == raw["reference_period"]
    assert public["precision"] == "occupation_cbo2002_6_digit"
    assert public["records"] == expected
    assert len(expected) == 993
    assert len({item[0] for item in expected}) == 38
    assert len({item[1] for item in expected}) == 27
    assert next(row[2] for row in expected if row[:2] == ["accountant", "SP"]) == 6266


def test_brazil_is_accessible_independently_of_production_deploy():
    main = (ROOT / "docs/index.html").read_text(encoding="utf8")
    brazil = (ROOT / "docs/brazil.html").read_text(encoding="utf8")
    assert 'href="./brazil.html?occupation=accountant&uf=SP"' in main
    assert 'fetch("./data/br-rais-2025-states.json"' in brazil
    assert "earnwage-api.policlinicosdesantoandre.com" not in brazil
    assert 'data.records.find(r=>r[0]===job&&r[1]===uf)' in brazil
    assert "não recebem automaticamente a mediana nacional" in brazil
