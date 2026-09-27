"""Real source snapshot regression tests: no invented job wages."""
import json

import pytest
from fastapi.testclient import TestClient

from app import es_eaes_groups as es
from app.main import app


def test_exact_official_series_and_quality_note():
    c=es.catalogue()
    assert c["status"]=="available"
    assert c["group_count"]==17 and c["sex_count"]==3
    assert c["published_observations"]==856
    assert c["suppressed_or_missing"]==62
    assert c["high_variability_observations"]==29
    assert c["precision"]=="cno11_major_group"
    assert c["source_url"].endswith("t=28186")
    total=es.group_history("TOTAL")
    assert total["precision"]=="all_occupations"
    assert total["observations"][0]["year"]==2024
    assert total["observations"][0]["value"]==29540.26
    assert len(total["observations"])==17
    b=es.group_history("B")
    assert b["observations"][0]["value"]==40554.53
    assert "salud y la enseñanza" in b["group_label"]
    q=es.group_history("Q")
    assert q["status"]=="unavailable"
    assert all(x["value"] is None for x in q["observations"])


def test_negative_source_wage_is_high_variability_flag_not_negative_pay():
    j=es.group_history("J","women")
    item=next(x for x in j["observations"] if x["year"]==2024)
    assert item["value"]==24001.36
    assert item["sample_quality"]=="sample_100_to_500_high_variability"
    missing=next(x for x in j["observations"] if x["year"]==2023)
    assert missing["value"] is None and missing["status"]=="suppressed"
    assert missing["sample_quality"]=="sample_below_100"


def test_invalid_group_range_and_sex_fail_closed():
    for args in (("22","both",2008,2024),
                 ("B","both",2008,2025),
                 ("B","men",2024,2023),
                 ("B","all",2008,2024)):
        with pytest.raises(ValueError):
            es.group_history(*args)


def test_bad_raw_note_is_rejected_not_abs_without_validation(tmp_path):
    raw=json.loads(es.DEFAULT.read_text(encoding="utf-8"))
    entry=next(o for o in raw if
               o["MetaData"][0]["Codigo"]=="J" and
               o["MetaData"][1]["Nombre"]=="Mujeres")
    entry["Data"][0]["Notas"]=[]
    p=tmp_path/"invalid.json"
    p.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ValueError,match="negative"):
        es.group_history("J","women",path=p)


def test_api_uses_es_context_only_and_inventory_never_counts_as_exact_wages():
    with TestClient(app) as client:
        catalog=client.get("/v1/es/earnings/groups")
        assert catalog.status_code==200
        assert catalog.json()["published_observations"]==856
        group=client.get("/v1/es/earnings/groups/B",
                         params={"sex":"both","start_year":2024,"end_year":2024})
        assert group.status_code==200
        data=group.json()
        assert data["observations"][0]["value"]==40554.53
        assert data["precision"]=="cno11_major_group"
        assert client.get("/v1/es/earnings/groups/B",params={"sex":"invalid"}).status_code==422
        assert client.get("/v1/es/earnings/groups/22").status_code==422
        inv=client.get("/v1/data-inventory").json()
        assert inv["summary"]["es_ine_eaes_groups"]["published_observations"]==856
        assert inv["summary"]["es_ine_eaes_groups"]["group_count"]==17
        assert inv["deployment"]["source_snapshots_on_server"]["spain_ine_eaes_groups"] is True
        for occupation in ("doctor","nurse","psychologist"):
            view=client.get("/v1/earnwage/overview",params={
                "country":"ES","occupation":occupation}).json()
            assert view["annual_presentation"]["status"]=="unavailable"
            assert view["annual_presentation"]["value"] is None
            assert view["national_occupation_wage"]["status"]=="unavailable"
