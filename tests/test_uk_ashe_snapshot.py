"""Regression tests for the committed official ONS ASHE aggregate snapshot."""
import json

from app import uk_ashe_wages as uk


def test_committed_snapshot_is_expected_corrected_2025_source():
    obj=json.loads(uk.DEFAULT.read_text(encoding="utf-8"))
    assert obj["schema"]==1
    assert obj["reference_period"]=="2025"
    assert obj["release_status"]=="provisional"
    assert obj["preferred_measure"]=="median"
    assert len(obj["records"])==52
    assert len({r["occupation"] for r in obj["records"]})==26
    assert obj["rejected"]==[
        {"occupation":"dentist","soc2020":"2253","measure":"median",
         "reason":"suppressed_or_cv_over_20"},
        {"occupation":"dentist","soc2020":"2253","measure":"mean",
         "reason":"suppressed_or_cv_over_20"},
    ]


def test_committed_snapshot_selected_official_values_and_quality():
    obj=json.loads(uk.DEFAULT.read_text(encoding="utf-8"))
    rows={(r["occupation"],r["measure"]):r for r in obj["records"]}
    checks={
        ("software_developer","median"):(55587,3.0,"SOC2020:2134"),
        ("civil_engineer","median"):(50602,5.3,"SOC2020:2121"),
        ("pharmacist","median"):(47508,5.8,"SOC2020:2251"),
        ("physiotherapist","median"):(37917,3.7,"SOC2020:2221"),
        ("secondary_teacher","median"):(44246,1.6,"SOC2020:2313"),
        ("plumber","median"):(36563,3.8,"SOC2020:5315"),
        ("accountant","median"):(45538,5.8,"SOC2020:2421"),
    }
    for key,(value,cv,classification) in checks.items():
        row=rows[key]
        assert row["value"]==value
        assert row["cv_percent"]==cv
        assert row["classification"]==classification
        assert row["currency"]=="GBP" and row["unit"]=="GBP/year"


def test_committed_snapshot_contains_no_broad_earnwage_title():
    obj=json.loads(uk.DEFAULT.read_text(encoding="utf-8"))
    jobs={r["occupation"] for r in obj["records"]}
    assert "doctor" not in jobs
    assert "nurse" not in jobs
    assert "psychologist" not in jobs
    assert "manager" not in jobs
    assert "dentist" not in jobs
