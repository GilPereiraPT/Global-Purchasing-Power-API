from io import BytesIO
import pytest

from app import store
from app.north_america import canada_records, persist, wages, export_snapshot, load_snapshot, us_records


HEAD = ("NOC_CNP,NOC_Title_eng,prov,ER_Code_Code_RE,Median_Wage_Salaire_Median,"
        "Average_Wage_Salaire_Moyen,Annual_Wage_Flag_Salaire_annuel,Reference_Period\n")
ROWS = (
    "NOC_31301,Registered nurses and registered psychiatric nurses,NAT,ER00,41.50,43.10,0,2023-2024\n"
    "NOC_21300,Civil engineers,NAT,ER00,46.20,51.40,0,2023-2024\n"
    "NOC_31301,Registered nurses and registered psychiatric nurses,ON,ER35,40.00,41.00,0,2023-2024\n"
    "NOC_72200,Electricians (except industrial and power system),NAT,ER00,,37.00,0,2023-2024\n"
    "NOC_31301,Registered nurses and registered psychiatric nurses,NAT,ER00,999.00,999.00,2,2023-2024\n"
)


def test_canada_exact_noc_units_and_region(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "wages.sqlite"))
    rows = list(canada_records(HEAD + ROWS))
    assert len(rows) == 5
    assert persist(rows) == 5
    record = wages("CA", "nurse")
    assert record["geography"] == "national"
    assert record["observations"][0]["unit"] == "CAD/hour"
    assert {r["value"] for r in record["observations"]} == {41.5, 43.1}
    assert wages("CA", "manager")["status"] == "unavailable"
    snap = tmp_path / "snapshot.json"
    assert export_snapshot(snap) == 5
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "new.sqlite"))
    assert load_snapshot(snap) == 5
    assert wages("CA", "nurse")["status"] == "available"


def test_canada_refuses_wrong_schema_or_changed_title():
    with pytest.raises(ValueError, match="schema"):
        list(canada_records("wrong,columns\n1,2\n"))
    with pytest.raises(ValueError, match="title drift"):
        list(canada_records(HEAD + "NOC_31301,Software engineers,NAT,ER00,10,11,0,2024\n"))


def test_us_national_only(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["AREA", "OCC_CODE", "OCC_TITLE", "O_GROUP", "A_MEAN", "A_MEDIAN"])
    ws.append([99, "29-1141", "Registered Nurses", "detailed", 101420, 98700])
    ws.append([1, "29-1141", "Registered Nurses", "detailed", 123456, 120000])
    ws.append([99, "29-1141", "Registered Nurses", "broad", 999999, 999999])
    p = tmp_path / "bls.xlsx"
    wb.save(p)
    records = list(us_records(p, 2025))
    assert len(records) == 2
    assert {r[9] for r in records} == {"USD/year"}
    assert {r[10] for r in records} == {101420.0, 98700.0}
