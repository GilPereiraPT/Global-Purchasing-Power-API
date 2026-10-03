"""Project reviewed staging into a NEW offline economic API-compatible database.

Never overwrites an existing DB. Does not activate/configure/import production.
The source ledger is copied with provenance/version history. Any incomplete or
failed latest dataset run prevents projection; quarantine is excluded.
"""
import argparse
import json
from pathlib import Path
from app.bulk_core import BulkStore


def export(staging,destination):
    import sqlite3
    source=Path(staging).resolve(strict=True)
    destination=Path(destination).resolve()
    if destination.exists() or destination==source or 'public_html' in destination.parts:
        raise ValueError('Export requires a new private offline database')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src:
        for status, in src.execute('SELECT status FROM bulk_runs WHERE id IN (SELECT MAX(id) FROM bulk_runs GROUP BY provider,dataset)'):
            if status!='complete':raise ValueError('Latest dataset run is incomplete or failed')
        # Exclusive file creation prevents accidental overwrite/races.
        with destination.open('xb'):pass
        try:
            with sqlite3.connect(destination) as db:
                src.backup(db)
                db.executescript('''CREATE TABLE observations (
                    country TEXT NOT NULL,indicator TEXT NOT NULL,year INTEGER NOT NULL,
                    value REAL NOT NULL,imported_at TEXT NOT NULL,
                    PRIMARY KEY(country,indicator,year));
                CREATE TABLE refresh_log (
                    country TEXT NOT NULL,indicator TEXT NOT NULL,last_attempt TEXT NOT NULL,
                    last_success TEXT,status TEXT NOT NULL,error_type TEXT,
                    PRIMARY KEY(country,indicator));
                ''')
                from app.eurostat_economy import ensure_tables
                from app.bulk_core import utcnow
                ensure_tables(db)
                now=utcnow()
                wb,euro=[],[]
                for payload, in src.execute('SELECT payload FROM bulk_current'):
                    row=json.loads(payload)
                    if row['provider']=='world_bank':
                        wb.append((row['country'],row['indicator'],int(row['period']),float(row['value']),now))
                    elif row['provider']=='eurostat':
                        euro.append((row['country'],row['indicator'],row['period'],float(row['value']),now))
                    else:raise ValueError('Unknown export provider')
                db.executemany('INSERT INTO observations VALUES (?,?,?,?,?)',wb)
                db.executemany('INSERT INTO eurostat_observations VALUES (?,?,?,?,?)',euro)
                for country,indicator in {(r[0],r[1]) for r in wb}:
                    db.execute('INSERT INTO refresh_log VALUES (?,?,?,?,?,?)',(country,indicator,now,now,'available',None))
                for country,indicator in {(r[0],r[1]) for r in euro}:
                    db.execute('INSERT INTO eurostat_refresh VALUES (?,?,?,?,?,?)',(country,indicator,now,now,'available',None))
                db.commit()
            return {'world_bank':len(wb),'eurostat':len(euro),'production_modified':False}
        except Exception:
            destination.unlink(missing_ok=True)
            raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--staging',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(export(a.staging,a.destination)))

if __name__=='__main__':main()
