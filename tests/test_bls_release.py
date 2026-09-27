"""All figures in this fixture are manually transcribed from BLS national Table 1;
these tests check provenance, SOC identity and that no annualization occurs.
"""
import pytest
from app.bls_release_import import reviewed_rows
from app.north_america import BLS_NEWS_TABLE


def test_reviewed_bls_2025_extract():
    data = list(reviewed_rows())
    assert len(data) == 10
    assert len({r[1] for r in data}) == 10
    assert all(r[0] == "US" and r[2] == "national" for r in data)
    assert all(r[5] == "May 2025" and r[7] == "USD" and r[8] == "mean"
               and r[9] == "USD/year" and r[12] == BLS_NEWS_TABLE for r in data)
    values = {r[1]: r[10] for r in data}
    assert values["nurse"] == 101420
    assert values["software_developer"] == 148100
    assert values["electrician"] == 71490
    assert values["cybersecurity_specialist"] == 132510


def test_reviewed_bls_rejects_unverified_source(tmp_path):
    bad = tmp_path / "invalid.csv"
    bad.write_text(
        "occupation,soc,title,annual_mean_usd,source_url\n"
        "nurse,29-1141,Registered Nurses,100000,https://example.com/\n"
    )
    with pytest.raises(ValueError, match="Source must"):
        list(reviewed_rows(bad))
