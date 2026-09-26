import sqlite3

from fastapi.testclient import TestClient

import app.store as store
from app.catalog import OCCUPATIONS
from app.ilostat_import import (
    earnings_datasets, import_csv, salary, availability, parse_row,
)
from app.main import app

SAMPLE = """ref_area,source,indicator,sex,classif1,classif2,time,obs_value
PRT,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_2411,CUR_LCU,2024,2000.5
DEU,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_2221,CUR_LCU,2024,3200
IND,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_2411,CUR_LCU,2024,55000
BRA,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_2411,CUR_LCU,2024,6000
PAK,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_2411,CUR_LCU,2024,45000
PRT,SRC_A,EAR_TEST,SEX_M,OCU_ISCO08_2411,CUR_LCU,2024,90000
PRT,SRC_A,EAR_TEST,SEX_T,OCU_ISCO88_2411,CUR_LCU,2024,90000
PRT,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_24,CUR_LCU,2024,90000
PRT,SRC_A,EAR_TEST,SEX_T,OCU_ISCO08_2411,CUR_PPP,2024,90000
"""


def test_catalog_and_coverage():
    assert len(OCCUPATIONS) == 40
    assert len({x["id"] for x in OCCUPATIONS}) == 40


def test_catalogue_filters_annual_monthly_employee_occupation():
    found = earnings_datasets([
        {"id": "EAR_EXAMPLE_A", "indicator.label": "Average monthly earnings of employees by sex, occupation and currency"},
        {"id": "EAR_EXAMPLE_M", "indicator.label": "Average monthly earnings of employees by sex and occupation (local currency)"},
        {"id": "FOO_A", "indicator.label": "Employment by sex and occupation"},
    ])
    assert [x["id"] for x in found] == ["EAR_EXAMPLE_A"]


def test_import_strict_and_matrix(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "salary.sqlite3"))
    with store.connect() as db:
        count = import_csv(db, SAMPLE, "EAR_TEST_A",
                           "Average monthly earnings of employees by sex, occupation and currency")
    assert count == 5
    assert salary("PT", "accountant")["value"] == 2000.5
    assert salary("PT", "accountant")["geography"] == "national"
    assert salary("IN", "accountant")["currency"] == "INR"
    assert salary("PK", "accountant")["value"] == 45000
    assert salary("PT", "doctor")["status"] == "unavailable"
    matrix = availability()
    assert len(matrix["cells"]) == 480
    assert sum(x["status"] == "available" for x in matrix["cells"]) == 5
    with TestClient(app) as client:
        assert client.get("/v1/salaries/PT/accountant").json()["value"] == 2000.5
        assert client.get("/v1/salaries/availability/matrix").json()["countries"] == 12


def test_nonlocal_annual_currency_never_admitted():
    row = {"ref_area": "IND", "sex": "SEX_T", "time": "2024",
           "classif1": "OCU_ISCO08_2411", "classif2": "CUR_PPP", "obs_value": "1000"}
    assert parse_row(row, "EAR_TEST_A",
                     "Average monthly earnings of employees by sex occupation and currency") is None
