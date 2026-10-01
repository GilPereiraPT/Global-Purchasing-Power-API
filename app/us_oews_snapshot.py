"""Export/import the compact, source-attributed OEWS release used by EarnWage."""
import json
from pathlib import Path
from app import us_oews
from app.north_america import US_SOC

DEFAULT = "data/us_oews_curated.json"


def export_snapshot(path=DEFAULT):
    codes = sorted({pair[0] for pair in US_SOC.values()})
    records = []
    with us_oews.connect() as db:
        us_oews.init(db)
        placeholders = ",".join("?" for _ in codes)
        sql = ("SELECT " + ",".join(us_oews.DB_COLUMNS) +
               " FROM us_oews WHERE occ_code IN (" + placeholders +
               ") AND o_group='detailed' AND naics IN ('000000','0')" +
               " AND own_code IN ('1235','') AND " +
               "(area_type IN ('1','1.0','2','2.0') OR area IN ('99','99.0'))")
        for row in db.execute(sql, codes):
            records.append(dict(zip(us_oews.DB_COLUMNS, row)))
    national = [r for r in records if r["area"] in ("99", "99.0") or r["area_title"] == "U.S."]
    states = {r["prim_state"] for r in records if r["area_type"] in ("2", "2.0") and r["prim_state"]}
    if len(national) < 20 or len(states) < 40:
        raise ValueError("Official US release incomplete: national occupations or states missing")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"schema": 1, "source_url": us_oews.BLS_TABLE,
                                  "records": records}, separators=(",", ":"), ensure_ascii=False),
                      encoding="utf-8")
    return {"observations": len(records), "national": len(national), "states": len(states)}


def load_snapshot(path=DEFAULT):
    path = Path(path)
    if not path.exists():
        return 0
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema") != 1 or not isinstance(obj.get("records"), list):
        raise ValueError("Invalid US OEWS snapshot")
    allowed = {v[0] for v in US_SOC.values()}
    rows = obj["records"]
    if not rows:
        raise ValueError("Empty US OEWS snapshot")
    for r in rows:
        if r.get("occ_code") not in allowed or r.get("o_group") != "detailed":
            raise ValueError("Unexpected SOC classification")
        if r.get("reference_period") != "May 2025" or r.get("published_year") != 2025:
            raise ValueError("Unexpected OEWS reference period")
        if r.get("naics") not in ("000000","0") or r.get("own_code") not in ("1235",""):
            raise ValueError("Unexpected occupation scope")
        if r.get("area_type") not in ("1","1.0","2","2.0") and r.get("area") not in ("99","99.0"):
            raise ValueError("Unexpected OEWS geography")
        if not any(isinstance(r.get(k.lower()), (int,float)) for k in us_oews.WAGE_FIELDS):
            raise ValueError("Missing OEWS wage")
    return us_oews.persist(rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()
    if args.export:
        print(json.dumps(export_snapshot()))
    elif args.load:
        print(json.dumps({"loaded": load_snapshot()}))
    else:
        parser.error("Specify --export or --load")
