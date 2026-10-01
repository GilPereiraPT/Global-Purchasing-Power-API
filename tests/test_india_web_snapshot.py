"""Guard against India PLFS website/API drift and accidentally exact salary labels."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data/in_plfs_2025_nco.json"
WEB = ROOT / "docs/data/india-plfs-2025-nco.json"


def snapshot():
    from app.in_nco_crosswalk import CONTEXT
    raw = json.loads(CANONICAL.read_text(encoding="utf8"))
    if raw["schema"] != 1 or raw["precision"] != "broad_nco2015_three_digit_group":
        raise ValueError("Unexpected canonical India dataset")
    records = [[x["nco2015_code"], "" if x["geography"] == "national" else x["state_code"],
                x["mean_monthly_earnings"], x["state_name"] or ""]
               for x in raw["records"]]
    return {"schema": 1, "period": raw["period"],
            "precision": raw["precision"], "source": raw["source_url"],
            "underlying": raw["underlying_official_source_url"],
            "license": raw["reuse_license"],
            "description": "Preprocessed PLFS 2025 descriptive NCO group means, not exact profession salaries",
            "mapping": {job: group for job, (group, _) in CONTEXT.items()},
            "records": records}


def test_static_snapshot_matches_canonical_data_and_mapping():
    expected = snapshot()
    actual = json.loads(WEB.read_text(encoding="utf8"))
    assert actual == expected, "Website India snapshot is outdated: regenerate it from canonical data"
    assert len(actual["records"]) == 597
    assert len(actual["mapping"]) == 31
    national = next(r for r in actual["records"] if r[0] == "251" and r[1] == "")
    maharashtra = next(r for r in actual["records"] if r[0] == "251" and r[1] == "27")
    assert national[2] == 54550.45
    assert maharashtra[2] == 58942.46


def test_main_web_contains_india_static_salary_flow():
    text = (ROOT / "docs/index.html").read_text(encoding="utf8")
    assert 'id="indiaMainPanel"' in text
    assert "async function renderIndiaMain()" in text
    assert 'renderIndiaMain();' in text
    assert "./data/india-plfs-2025-nco.json" in text
    assert "snap.mapping[job]" in text
    assert 'case "salary":return ["IN","DE","BR"].includes(c)?' in text
    assert 'renderIndiaMain' in text
    assert "não é salário específico" in text


if __name__ == "__main__":
    WEB.parent.mkdir(exist_ok=True, parents=True)
    WEB.write_text(json.dumps(snapshot(), ensure_ascii=False, separators=(",", ":")), encoding="utf8")


def test_india_direct_lookup_is_linked_and_does_not_depend_on_production_api():
    main = (ROOT / "docs/index.html").read_text(encoding="utf8")
    page = (ROOT / "docs/india.html").read_text(encoding="utf8")
    assert 'href="./india.html?occupation=software_developer&region=27"' in main
    assert 'fetch("./data/india-plfs-2025-nco.json"' in page
    assert 'earnwage-api.policlinicosdesantoandre.com' not in page
    assert 'data.mapping[occupation]' in page
    assert 'new URLSearchParams(location.search)' in page
    assert "Não substituída pela média nacional" in page
    assert "não salários exatos" in page
