import pytest

from scripts.in_rural_staging import audit

HEADER = "S.No,Year,Month,State,Occupation,Item,Men,Women\n"


def test_conflicting_duplicates_and_suppression_remain_private():
    body = (HEADER + "1,2025-2026,Jan,STATE,Non-Agriculture,Electrician,100,@\n"
            + "2,2025-2026,Jan,STATE,Non-Agriculture,Electrician,200,-\n").encode()
    report, staging = audit(body)
    assert report["source_rows"] == 2
    assert report["source_cells"] == 4
    assert report["duplicate_rows"] == 1
    assert report["conflicting_identities"] == 1
    assert report["source_cell_status_counts"] == {
        "positive_numeric": 2, "fewer_than_five_quotes": 1, "operation_unavailable": 1}
    assert staging["publication_status"] == "private_staging_only"
    assert staging["rows"][0]["quality_status"] == "conflicting_duplicates"
    assert staging["rows"][0]["original_values"] == [("100", "@"), ("200", "-")]


@pytest.mark.parametrize("value", ["NaN", "-1", "0", "unknown"])
def test_unreviewed_values_are_rejected(value):
    body = (HEADER + f"1,2025-2026,Jan,STATE,Agriculture,Carpenter,{value},-\n").encode()
    with pytest.raises(ValueError):
        audit(body)
