from app import ch_bfs_wages as ch

def test_swiss_mapping_is_submajor_not_exact():
    assert ch.SUBMAJOR["accountant"] == "24"
    assert ch.SUBMAJOR["nurse"] == "22"
    assert ch.SUBMAJOR["software_developer"] == "25"

def test_missing_snapshot_never_invents_wage(tmp_path):
    result=ch.context("accountant",tmp_path/"missing.json")
    assert result["status"]=="unavailable"
    assert result["precision"]=="ch_isco19_submajor_group"
