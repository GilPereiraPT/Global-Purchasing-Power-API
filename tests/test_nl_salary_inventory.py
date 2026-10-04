import json
import sqlite3
import pytest
from app import nl_cbs_wages
from app.salary_inventory_export import export


def database(tmp_path):
    path = tmp_path / 'wages.sqlite3'
    snapshot = json.loads(nl_cbs_wages.DEFAULT.read_text())
    rows = nl_cbs_wages.validate_snapshot(snapshot)
    with sqlite3.connect(path) as db:
        nl_cbs_wages.init(db)
        db.executemany('INSERT INTO nl_cbs_wages VALUES (' + ','.join('?' for _ in range(20)) + ')', rows)
    return path


def test_nl_export_preserves_identity_and_values(tmp_path):
    path = database(tmp_path)
    before = path.read_bytes()
    out = tmp_path / 'inventory'
    report = export(path, out, authorization='owner-requested-NL-reconciliation')
    records = json.loads((out / 'nl_cbs_wages.json').read_text())['records']
    assert report['tables']['nl_cbs_wages']['rows'] == 21
    assert report['tables']['nl_cbs_wages']['primary_key'] == ['country', 'occupation', 'reference_period', 'source']
    assert records[0]['currency'] == 'EUR'
    assert records[0]['unit'] == 'EUR/hour'
    assert records[0]['publication_status']
    assert path.read_bytes() == before


@pytest.mark.parametrize('field,value', [('source_url','https://datasets.cbs.nl/odata/v1/CBS/other'), ('source_page','https://evil.example'), ('employees_thousand', -1)])
def test_nl_invalid_metadata_rejected(tmp_path,field,value):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE nl_cbs_wages SET ' + field + '=?', (value,))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        export(path, tmp_path/'inventory', authorization='owner-requested-NL-reconciliation')
    assert path.read_bytes() == before
