import csv
import pytest
from app.bulk_core import BulkStore,digest
from scripts.bulk_quarantine_audit import audit
from tests.test_bulk_core import observation,artifact


def test_every_quarantined_version_is_classified_without_database_writes(tmp_path):
    path=tmp_path/'stage.sqlite3';store=BulkStore(path)
    checksum=artifact(store,tmp_path)
    store.ingest('audit',checksum,[observation('100','2024'),observation('200','2025')]);store.close()
    before=digest(path);output=tmp_path/'audit.csv';result=audit(path,output)
    assert digest(path)==before
    assert result['reviewed']==1 and result['automatically_approved']==0
    assert result['assessment_categories']=={'monetary_unit_or_exchange_rate_review':1}
    with output.open() as f:rows=list(csv.DictReader(f))
    assert rows[0]['manual_assessment']=='required' and rows[0]['disposition']=='retain_quarantine'
    with pytest.raises(ValueError):audit(tmp_path/'absent.sqlite3',tmp_path/'absent.csv')
    assert not (tmp_path/'absent.sqlite3').exists()
