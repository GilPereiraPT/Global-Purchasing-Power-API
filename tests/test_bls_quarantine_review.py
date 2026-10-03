import copy
from app.bulk_core import BulkStore
from app.bulk_bls import observations,url
from scripts.bls_quarantine_review import review
from tests.test_bulk_bls import release


def test_complete_grouping_read_only_and_representative_sample(tmp_path):
 archive,_=release(tmp_path);path=tmp_path/'stage.sqlite3';store=BulkStore(path)
 rows=list(observations(archive,2025,{}))
 old=copy.deepcopy(rows)
 for r in old:r.update(period='2024',original_period='May 2024',source_url=url(2024))
 try:
  store.artifact({'sha256':'a'*64,'url':url(2024)})
  store.artifact({'sha256':'b'*64,'url':url(2025)})
  store.ingest('old','a'*64,old)
  for r in rows:r['value']=str(float(r['value'])*2)
  store.ingest('new','b'*64,rows)
 finally:store.close()
 raw=path.read_bytes();report=review(path)
 assert report['quarantined_observations']==12 and report['approved_by_review']==0
 assert sum(r['count'] for r in report['groups'])==12
 assert report['dimensions']['magnitude']=={'over_50_to_100_percent':12}
 assert report['sample'][0]['previous_period']=='2024'
 assert path.read_bytes()==raw
