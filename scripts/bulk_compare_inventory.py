"""Compare explicit local staging with an authorized observation-level JSON export."""
import argparse
import json
import sqlite3
from pathlib import Path
from app.bulk_inventory_export import compare


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--staging',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--authorization',required=True,help='Reference to the export owner authorization')
    a=p.parse_args()
    if not a.staging.is_file() or a.staging.is_symlink():raise ValueError('Explicit local staging file required')
    with sqlite3.connect(a.staging.resolve().as_uri()+'?mode=ro',uri=True) as db:
        rows=(json.loads(r[0]) for r in db.execute('SELECT payload FROM bulk_current'))
        print(json.dumps(compare(rows,a.inventory,authorization=a.authorization)))

if __name__=='__main__':main()
