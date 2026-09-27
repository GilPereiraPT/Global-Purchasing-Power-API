import csv
import json
from app.ilostat_groups import build_snapshot, group_salary


def test_group_salaries_are_not_individual_jobs(tmp_path):
    path = tmp_path / "official.csv"
    columns = ["ref_area","source","indicator","sex","classif1",
               "classif2","time","obs_value"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for occupation, unit, value in [
            ("OCU_ISCO08_2","CUR_TYPE_LCU","2000"),
            ("OCU_ISCO08_2","CUR_TYPE_USD","2200"),
            ("OCU_ISCO08_2","CUR_TYPE_PPP","2400"),
            ("OCU_ISCO08_2221","CUR_TYPE_LCU","3000"),
            ("OCU_SKILL_L3-4","CUR_TYPE_LCU","4000"),
        ]:
            writer.writerow(dict(ref_area="PRT", source="BX:1",
                indicator="EAR_EMTA_SEX_OCU_CUR_NB",sex="SEX_T",
                classif1=occupation,classif2=unit,time="2025",obs_value=value))
    snapshot = build_snapshot(path)
    assert len(snapshot["observations"]) == 3
    target = tmp_path / "snapshot.json"
    target.write_text(json.dumps(snapshot))
    result = group_salary("PT", "2", target)
    assert result["values"]["local_currency"]["value"] == 2000
    assert result["values"]["ppp"]["value"] == 2400
    assert result["precision"] == "isco08_major_group"


def test_multiple_sources_are_ambiguous(tmp_path):
    path = tmp_path / "official.csv"
    path.write_text("ref_area,source,indicator,sex,classif1,classif2,time,obs_value\n"
                    "PRT,BX:1,EAR_EMTA_SEX_OCU_CUR_NB,SEX_T,OCU_ISCO08_2,CUR_TYPE_LCU,2025,2000\n"
                    "PRT,BX:2,EAR_EMTA_SEX_OCU_CUR_NB,SEX_T,OCU_ISCO08_2,CUR_TYPE_LCU,2025,2500\n")
    target = tmp_path / "snapshot.json"
    target.write_text(json.dumps(build_snapshot(path)))
    assert group_salary("PT","2",target)["values"]["local_currency"]["status"] == "ambiguous"
