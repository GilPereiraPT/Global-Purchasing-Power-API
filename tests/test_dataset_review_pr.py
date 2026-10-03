import hashlib
import json
from pathlib import Path
import pytest
from scripts import dataset_review_pr as review

ENV = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY=review.REPOSITORY,
           GITHUB_REF='refs/heads/main', GITHUB_SHA='a'*40,
           GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1')

@pytest.mark.parametrize('field,value', [('GITHUB_EVENT_NAME','push'),('GITHUB_EVENT_NAME','schedule'),
 ('GITHUB_EVENT_NAME','pull_request'),('GITHUB_REF','refs/heads/feature'),
 ('GITHUB_REPOSITORY','fork/repo'),('GITHUB_SHA','invalid'),('GITHUB_RUN_ID','../main')])
def test_reject_unattended_and_untrusted(field,value):
 assert not review.authorized({**ENV,field:value})
 with pytest.raises(ValueError):review.publish(['data/ca_province_wages.json'],{**ENV,field:value})

def test_only_data_branch_created(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);(tmp_path/'data').mkdir()
 path='data/ca_province_wages.json';Path(path).write_text('{"records":[]}')
 calls=[]
 def api(endpoint,payload=None):
  calls.append((endpoint,payload))
  if endpoint=='commits/main':return {'sha':'a'*40,'commit':{'tree':{'sha':'b'*40}}}
  if endpoint.startswith('git/trees/') :return {'tree':[]}
  if endpoint=='pulls':return {'html_url':'https://example.test/pr'}
  return {'sha':'c'*40}
 monkeypatch.setattr(review,'api',api)
 assert review.publish([path],ENV)['status']=='review_required'
 assert next(p for e,p in calls if e=='git/refs')['ref']=='refs/heads/data-review/123-1'
 assert next(p for e,p in calls if e=='git/commits')['parents']==['a'*40]
 assert next(p for e,p in calls if e=='git/trees')['tree'][0]['path']==path
 assert not any(e.startswith('git/refs/heads/main') for e,p in calls)

def test_stale_main_and_unsafe_paths(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);(tmp_path/'data').mkdir();Path('data/ca_province_wages.json').write_text('{}')
 monkeypatch.setattr(review,'api',lambda *args:{'sha':'d'*40})
 with pytest.raises(ValueError,match='advanced'):review.publish(['data/ca_province_wages.json'],ENV)
 with pytest.raises(ValueError,match='Unapproved'):review.publish(['app/native_wsgi.py'],ENV)
 Path('data/ca_province_wages.json').unlink();Path('data/ca_province_wages.json').symlink_to('/tmp/private')
 with pytest.raises(ValueError):review.publish(['data/ca_province_wages.json'],ENV)

def test_workflow_writers_all_require_review():
 workflows=Path('.github/workflows')
 assert len(list(workflows.glob('*.yml')))==35
 writers=[]
 for path in workflows.glob('*.yml'):
  text=path.read_text()
  assert 'git push' not in text,path
  if 'dataset_review_pr.py' in text:
   writers.append(path)
   assert "github.event_name == 'workflow_dispatch'" in text
   assert "github.ref == 'refs/heads/main'" in text
   assert "github.repository == '"+review.REPOSITORY+"'" in text
   assert 'persist-credentials: false' in text
   name=text.split('python scripts/dataset_review_pr.py ')[1].splitlines()[0].strip()
   assert name in review.ALLOWED
 assert len(writers)==10
