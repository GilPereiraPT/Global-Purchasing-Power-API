"""Exercise the actual WSGI archive with isolated authentic hourly history."""
import json
import os
import subprocess
import sys
from scripts import deploy_runtime as runtime
from tests.test_deployment_recovery import package
from tests.test_nl_cbs_history import reviewed


def test_packaged_wsgi_reads_history_without_auto_loading_private_artifacts(package,tmp_path,monkeypatch):
    _,review=reviewed(tmp_path,monkeypatch)
    root=tmp_path/'passenger';root.mkdir();runtime.install(root,package)
    members,_=runtime.read_archive(package)
    assert 'app/nl_cbs_wages.py' in members
    assert not any('cbs-history' in n or n.endswith(('.body','.sqlite3','.zip')) or n.startswith(('tests/','docs/')) for n in members)
    # Existing archive rules include scripts, but never invoke this offline command.
    assert 'scripts/nl_cbs_history.py' in members
    rows=tmp_path/'sample-rows.json';rows.write_text(json.dumps(review['records']))
    script=r'''
import io,json,os,sqlite3,sys
from pathlib import Path
from app import nl_cbs_wages as nl,native_wsgi
from passenger_wsgi import application
native_wsgi.initialize=lambda:None
nl.load_snapshot()
with sqlite3.connect(os.environ['GPP_CACHE_DB']) as db:
 rows=json.loads(Path(sys.argv[1]).read_text())
 db.executemany('INSERT OR IGNORE INTO nl_cbs_wages VALUES ('+','.join('?' for _ in nl.FIELDS)+')',
                [tuple(row[field] for field in nl.FIELDS) for row in rows])
assert nl.wages('NL','software_developer')['value']==34.5
status=[]
env={'PATH_INFO':'/v1/earnwage/history','REQUEST_METHOD':'GET',
     'QUERY_STRING':'country=NL&occupation=software_developer&start_year=2018&end_year=2025',
     'wsgi.input':io.BytesIO(b'')}
reply=json.loads(b''.join(application(env,lambda s,h:status.append(s))))
assert status[0].startswith('200')
assert reply['exact_occupation_history']['precision']==nl.PRECISION
by_year={r['year']:r for r in reply['exact_occupation_history']['observations']}
assert by_year[2018]['status']=='unavailable'
assert by_year[2019]['reported_hourly']['value']==26.3
assert by_year[2019]['annual_presentation']['status']=='unavailable'
assert by_year[2019]['source_observations'][0]['publication_status']=='definitive'
assert by_year[2025]['source_observations'][0]['publication_status']=='provisional'
assert 'fastapi' not in sys.modules
assert not Path(os.environ['EARNWAGE_INSIGHTS_DB']).exists()
print('packaged CBS historical WSGI verified')
'''
    env={**os.environ,'GPP_CACHE_DB':str(tmp_path/'wages.sqlite3'),
         'EARNWAGE_INSIGHTS_DB':str(tmp_path/'never-created.sqlite3')}
    process=subprocess.run([sys.executable,'-c',script,str(rows)],cwd=root,env=env,
                           capture_output=True,text=True,timeout=30)
    assert process.returncode==0,process.stderr
