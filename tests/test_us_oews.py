from zipfile import ZipFile

from openpyxl import Workbook
import pytest

from app import store
from app.us_oews import (
    catalogue, coverage, import_zip, persist, wages, workbook_records,
)


def make_book(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "national"
    ws.append([
        "AREA", "AREA_TITLE", "AREA_TYPE", "PRIM_STATE", "NAICS", "NAICS_TITLE",
        "I_GROUP", "OWN_CODE", "OCC_CODE", "OCC_TITLE", "O_GROUP",
        "TOT_EMP", "H_MEAN", "A_MEAN", "H_PCT10", "H_PCT25", "H_MEDIAN",
        "H_PCT75", "H_PCT90", "A_PCT10", "A_PCT25", "A_MEDIAN",
        "A_PCT75", "A_PCT90",
    ])
    ws.append([
        99, "U.S.", 1, "", "000000", "Cross-industry", "cross-industry", "1235",
        "15-1252", "Software Developers", "detailed",
        1800000, 69.50, 144560, 38.00, 48.00, 65.00, 85.00, 105.00,
        79040, 99840, 135200, 176800, 218400,
    ])
    ws.append([
        99, "U.S.", 1, "", "000000", "Cross-industry", "cross-industry", "1235",
        "29-1141", "Registered Nurses", "detailed",
        3300000, 50.20, 104420, "*", 39.00, 47.00, 58.00, "#",
        "*", 81120, 97760, 120640, "#",
    ])
    wb.save(path)


def test_full_oews_parser_keeps_percentiles_and_suppression(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "oews.sqlite"))
    book = tmp_path / "national.xlsx"
    make_book(book)
    rows = list(workbook_records(book, 2025))
    assert len(rows) == 2
    nurse = next(row for row in rows if row["occ_code"] == "29-1141")
    assert nurse["a_mean"] == 104420
    assert nurse["h_pct10"] is None
    assert nurse["a_pct90"] is None
    assert persist(rows, replace_year=2025) == 2

    result = wages("15-1252")
    assert result["status"] == "available"
    assert result["observations"][0]["a_median"] == 135200
    assert result["observations"][0]["h_median"] == 65


def test_zip_import_and_catalogue(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "oews.sqlite"))
    book = tmp_path / "national.xlsx"
    make_book(book)
    archive = tmp_path / "oesm25all.zip"
    with ZipFile(archive, "w") as zf:
        zf.write(book, arcname="oesm25nat/national.xlsx")
        zf.writestr("notes/readme.txt", "not a workbook")

    result = import_zip(archive, 2025)
    assert result["rows"] == 2
    assert result["workbooks"] == ["oesm25nat/national.xlsx"]
    cat = catalogue("software")
    assert cat["count"] == 1
    assert cat["occupations"][0]["soc"] == "15-1252"
    stats = coverage()
    assert stats["rows"] == 2
    assert stats["occupations"] == 2


def test_parser_rejects_non_oews_workbook(tmp_path):
    wb = Workbook()
    wb.active.append(["foo", "bar"])
    p = tmp_path / "bad.xlsx"
    wb.save(p)
    with pytest.raises(ValueError, match="No compatible"):
        list(workbook_records(p, 2025))


def test_wages_validates_soc(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "oews.sqlite"))
    with pytest.raises(ValueError, match="SOC"):
        wages("software")


def test_state_wages_never_fall_back_to_national(tmp_path, monkeypatch):
    from app.us_oews import curated_state_wages
    from app.earnwage_queries import overview
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "states.sqlite"))
    national = {
        "reference_period": "May 2025", "published_year": 2025,
        "source_file": "national.xlsx", "area": "99", "area_title": "U.S.",
        "area_type": "1", "prim_state": "", "naics": "000000",
        "naics_title": "Cross-industry", "i_group": "cross-industry",
        "own_code": "1235", "occ_code": "15-1252",
        "occ_title": "Software Developers", "o_group": "detailed",
        "a_mean": 120000, "a_median": 110000, "h_mean": 60,
        "h_median": 55, "source_url": "https://www.bls.gov/oes/tables.htm",
    }
    california = {**national, "source_file": "states.xlsx",
                  "area": "0600000", "area_title": "California",
                  "area_type": "2", "prim_state": "CA",
                  "a_mean": 160000, "a_median": 150000}
    metro = {**national, "source_file": "metros.xlsx",
             "area": "41860", "area_title": "San Francisco",
             "area_type": "4", "prim_state": "CA", "a_mean": 190000}
    industry = {**california, "source_file": "industry.xlsx",
                "naics": "541500", "naics_title": "Computer Systems Design",
                "i_group": "4-digit", "a_mean": 210000}
    assert persist([national, california, metro, industry], replace_year=2025) == 4
    ca = curated_state_wages("software_developer", "CA")
    assert ca["status"] == "available"
    assert ca["metrics"]["a_mean"] == 160000
    assert ca["metrics"]["a_median"] == 150000
    assert ca["scope"] == "state_wide_cross_industry"
    assert curated_state_wages("software_developer", "TX")["status"] == "unavailable"
    assert curated_state_wages("doctor", "CA")["status"] == "unavailable"
    with pytest.raises(ValueError, match="state"):
        curated_state_wages("software_developer", "XX")
    # Overview preserves distinct national and regional labels.
    view = overview("US", "software_developer", region="CA")
    assert view["national_occupation_wage"]["geography"] == "national"
    assert view["regional_occupation_wage"]["geography"] == "state"
    assert view["regional_occupation_wage"]["metrics"]["a_mean"] == 160000
