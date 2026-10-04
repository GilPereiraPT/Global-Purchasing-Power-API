"""Operator export runs only against isolated databases, never application init."""
import hashlib
import json
from pathlib import Path
import sqlite3
import pytest
from app import north_america, us_oews, ca_province_wages
from scripts.deploy_runtime import allowed
from app import salary_inventory_export as operator

PATH = Path(__file__).resolve().parents[1] / 'docs/bulk/operator/export_salary_inventory.py'


def source(tmp_path):
    tmp_path.chmod(0o700)
    path = tmp_path / 'wages.sqlite3'
    with sqlite3.connect(path) as db:
        us_oews.init(db);north_america.init(db);ca_province_wages.init(db)
        db.execute('CREATE TABLE private_credentials (secret TEXT)')
        db.execute("INSERT INTO private_credentials VALUES ('never-export')")
        db.execute("INSERT INTO us_oews (reference_period,published_year,source_file,occ_code,occ_title,source_url,a_mean) VALUES ('May 2021',2021,'source.xlsx','15-1252','Software Developers','https://www.bls.gov/oes/tables.htm',120990)")
    return path


def test_export_preserves_stored_values_and_never_writes_source(tmp_path):
    path=source(tmp_path);before=path.read_bytes();out=tmp_path/'export'
    report=operator.export(path,out,authorization='owner-approved-inventory-only')
    assert report['total_rows']==1 and report['scope']=='all_rows_of_listed_salary_tables_only'
    rows=json.loads((out/'us_oews.json').read_text())['records']
    assert rows[0]['a_mean']==120990 and rows[0]['a_median'] is None
    assert rows[0]['reference_period']=='May 2021'
    for record in report['tables'].values():
        if record['status'] == 'absent':
            continue
        raw=(out/record['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==record['sha256']
        assert b'never-export' not in raw
    assert path.read_bytes()==before
    assert out.stat().st_mode & 0o777==0o700
    assert all(p.stat().st_mode & 0o777==0o600 for p in out.iterdir())
    assert not allowed('docs/bulk/operator/export_salary_inventory.py')


def test_live_wal_values_visible_without_application_import_or_checkpoint(tmp_path):
    path=source(tmp_path)
    with sqlite3.connect(path) as live:
        live.execute('PRAGMA journal_mode=WAL')
        live.execute('UPDATE us_oews SET a_mean=123456');live.commit()
        wal=Path(str(path)+'-wal');before=wal.read_bytes()
        operator.export(path,tmp_path/'export',authorization='approved')
        assert json.loads((tmp_path/'export/us_oews.json').read_text())['records'][0]['a_mean']==123456
        assert wal.read_bytes()==before


def test_absent_tables_recorded_without_initialization(tmp_path):
    tmp_path.chmod(0o700);path=tmp_path/'empty.sqlite3'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE unrelated(value TEXT)')
    report=operator.export(path,tmp_path/'export',authorization='approved')
    assert all(r=={'status':'absent','rows':0} for r in report['tables'].values())
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('unrelated',)]


@pytest.mark.parametrize('failure',['missing','authorization','symlink','existing','schema','space','limit','timeout'])
def test_export_fails_closed_preserving_database(tmp_path,monkeypatch,failure):
    path=source(tmp_path);out=tmp_path/'export';auth='approved'
    if failure=='missing':path=tmp_path/'missing.sqlite3'
    elif failure=='authorization':auth=''
    elif failure=='symlink':link=tmp_path/'link';link.symlink_to(path);path=link
    elif failure=='existing':out.mkdir();(out/'keep').write_text('keep')
    elif failure=='schema':
        with sqlite3.connect(path) as db:db.execute('ALTER TABLE us_oews RENAME COLUMN a_mean TO unexpected')
    elif failure=='space':
        monkeypatch.setattr(operator.shutil,'disk_usage',lambda p:type('Space',(),{'free':0})())
    elif failure=='limit':monkeypatch.setattr(operator,'MAX_BYTES',1)
    elif failure=='timeout':monkeypatch.setattr(operator,'TIMEOUT_SECONDS',-1)
    before=path.read_bytes() if path.is_file() else None
    with pytest.raises((ValueError,OSError)):operator.export(path,out,authorization=auth)
    if before is not None:assert path.read_bytes()==before
    else:assert not path.exists()
    if failure=='existing':assert (out/'keep').read_text()=='keep'
    else:assert not out.exists()
