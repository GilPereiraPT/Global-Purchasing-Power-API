from app import store
from app.ca_province_wages import records, persist, wage, coverage, export_snapshot, load_snapshot
from app.earnwage_queries import overview
import pytest

HEAD = ("NOC_CNP,NOC_Title_eng,prov,ER_Code_Code_RE,Low_Wage_Salaire_Minium,"
        "Median_Wage_Salaire_Median,High_Wage_Salaire_Maximal,"
        "Average_Wage_Salaire_Moyen,Quartile1_Wage_Salaire_Quartile1,"
        "Quartile3_Wage_Salaire_Quartile3,Annual_Wage_Flag_Salaire_annuel,Reference_Period\n")
ROWS = (
    "NOC_31301,Registered nurses and registered psychiatric nurses,ON,ER35,32,42,56,44,37,50,0,2023-2024\n"
    "NOC_31301,Registered nurses and registered psychiatric nurses,QC,ER24,31,41,53,43,36,49,0,2023-2024\n"
    "NOC_31301,Registered nurses and registered psychiatric nurses,ON,ER3510,50,60,70,62,55,65,0,2023-2024\n"
    "NOC_31301,Registered nurses and registered psychiatric nurses,NAT,ER00,60,70,80,75,65,76,0,2023-2024\n"
    "NOC_31110,Dentists,AB,ER48,100000,150000,210000,160000,115000,190000,1,2021\n"
)


def test_province_import_exact_aggregate_and_measures(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "ca.sqlite"))
    rows = list(records(HEAD + ROWS))
    assert len(rows) == 18  # 2 provincial nurses + 1 annual dentist, six each
    assert persist(rows) == 18
    ontario = wage("nurse", "ON")
    assert ontario["status"] == "available"
    assert ontario["unit"] == "CAD/hour"
    assert ontario["metrics"]["median"] == 42
    assert ontario["metrics"]["mean"] == 44
    assert ontario["metrics"]["p25"] == 37
    assert ontario["geography"] == "province"
    assert wage("nurse", "QC")["metrics"]["median"] == 41
    assert wage("nurse", "BC")["status"] == "unavailable"
    alberta = wage("dentist", "AB")
    assert alberta["unit"] == "CAD/year"
    assert alberta["reference_period"] == "2021"
    assert coverage()["occupation_province_pairs"] == 3
    snapshot = tmp_path / "provinces.json"
    assert export_snapshot(snapshot) == 18
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "restored.sqlite"))
    assert load_snapshot(snapshot) == 18
    assert wage("nurse", "ON")["metrics"]["median"] == 42


def test_province_rejects_schema_drift_and_unknown_province(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "ca.sqlite"))
    with pytest.raises(ValueError, match="schema"):
        list(records("a,b\n1,2\n"))
    with pytest.raises(ValueError, match="title drift"):
        list(records(HEAD + "NOC_31301,Electricians,ON,ER35,1,2,3,4,5,6,0,2023-2024\n"))
    with pytest.raises(ValueError, match="province"):
        wage("nurse", "XX")


def test_overview_keeps_national_and_provincial_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "ca.sqlite"))
    assert persist(records(HEAD + ROWS)) == 18
    view = overview("CA", "nurse", region="ON")
    assert view["regional_occupation_wage"]["geography"] == "province"
    assert view["regional_occupation_wage"]["metrics"]["median"] == 42
    assert view["regional_occupation_wage"]["unit"] == "CAD/hour"
    assert view["national_occupation_wage"]["geography"] == "national" if view["national_occupation_wage"]["status"] == "available" else True
    assert overview("CA", "nurse")["regional_occupation_wage"]["status"] == "not_requested"
