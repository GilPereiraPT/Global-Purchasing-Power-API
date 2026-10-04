"""Published federal anchors and fail-closed jurisdiction coverage, not tax returns."""
from decimal import Decimal as D
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tax_engine import calculate, monetary
from app.us_federal_benchmark import SCENARIO
from app.us_tax_jurisdictions import coverage
from tests.test_us_federal_benchmark import facts
from tests.test_portugal_benchmark_2025 import wsgi


@pytest.mark.parametrize('state', ['TX', 'FL'])
def test_jurisdiction_zero_never_promotes_total_net(state):
    result = calculate('US', '100000', 2026, SCENARIO, state, us_facts=facts('100000'))
    amounts = {c['name']: c['amount'] for c in result['components']}
    assert amounts['state_income_tax_final'] == '0.00'
    assert amounts['local_income_tax'] is amounts['mandatory_state_employee_contributions'] is None
    if state == 'FL':
        assert amounts['employee_reemployment_contribution'] == '0.00'
    else:
        assert amounts['employee_unemployment_contribution'] is None
    assert result['status'] == 'partial' and result['net_income'] is None
    assert any('private/public' in rule for rule in result['limitations'])


def test_rule_evidence_missing_cannot_create_zero(monkeypatch):
    monkeypatch.setattr('app.us_tax_jurisdictions.sources_for', lambda urls: ({
        'url': urls[0], 'tax_year': 2026, 'verification_status': 'blocked'},))
    assert all(c['amount'] is None for c in coverage('FL')['components'])


def test_coverage_returns_fresh_metadata_and_no_other_state_zero():
    first = coverage('FL'); first['sources'][0]['verification_status'] = 'verified'
    assert coverage('FL')['sources'][0]['verification_status'] == 'parameters_reviewed'
    for state in (None, 'NY', 'CA', 'PA'):
        assert all(c['amount'] is None for c in coverage(state)['components'])


# Accumulated taxes explicitly published in Rev. Proc. 2025-32 Table 3;
# anchor +/- one dollar uses that table's adjoining rates, not our integrator.
@pytest.mark.parametrize('taxable,base,left,right', [
    ('12400','1240','.10','.12'), ('50400','5800','.12','.22'),
    ('105700','17966','.22','.24'), ('201775','41024','.24','.32'),
    ('256225','58448','.32','.35'),
])
@pytest.mark.parametrize('offset', [-1, 0, 1])
def test_federal_published_anchors_and_adjacent_dollars(taxable,base,left,right,offset):
    gross = str(D(taxable) + D('16100') + offset)
    result = calculate('US', gross, 2026, SCENARIO, 'TX', us_facts=facts(gross))
    amount = next(c['amount'] for c in result['components'] if c['name']=='federal_regular_income_tax_model')
    expected = D(base) + D(offset) * D(left if offset < 0 else right)
    assert amount == monetary(expected)


@pytest.mark.parametrize('gross,ss,medicare,additional', [
    ('184499','11438.94','2675.24','0.00'),
    ('184500','11439.00','2675.25','0.00'),
    ('184501','11439.00','2675.26','0.00'),
    ('199999','11439.00','2899.99','0.00'),
    ('200000','11439.00','2900.00','0.00'),
    ('200001','11439.00','2900.01','0.01'),
    ('200000.55','11439.00','2900.01','0.00'),
    ('200000.56','11439.00','2900.01','0.01'),
])
def test_fica_reference_thresholds_and_output_rounding(gross,ss,medicare,additional):
    result = calculate('US', gross, 2026, SCENARIO, 'FL', us_facts=facts(gross))
    amounts = {c['name']: c['amount'] for c in result['components']}
    assert amounts['federal_employee_social_security_model'] == ss
    assert amounts['federal_employee_medicare_model'] == medicare
    assert amounts['federal_employee_additional_medicare_model'] == additional
    assert result['net_income'] is None


@pytest.mark.parametrize('state', ['TX', 'FL', 'NY', 'CA', 'PA', None])
def test_http_parity_complete_and_missing_jurisdiction(state):
    params = dict(country='US', annual_gross='100000', tax_year='2026',
                  scenario=SCENARIO, us_facts=json.dumps(facts('100000')))
    if state is not None: params['region'] = state
    with TestClient(app) as client: response = client.get('/v1/tax/calculate',params=params)
    code, body = wsgi('/v1/tax/calculate', params)
    assert response.status_code == code == 200
    assert response.json() == body and body['net_income'] is None


def test_production_archive_wsgi_in_isolated_installation(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    from scripts.deploy_runtime import build, read_archive, write_files
    root = Path(__file__).resolve().parents[1]
    sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    archive = tmp_path / 'runtime.tgz'
    build(root, archive, sha)
    files, _ = read_archive(archive)
    assert 'app/us_tax_jurisdictions.py' in files
    assert 'data/us_tax_2026_source_evidence.json' in files
    assert not any(name.endswith(('.sqlite3','.db')) for name in files)
    isolated = tmp_path / 'runtime'; isolated.mkdir()
    write_files(isolated, files)
    params = dict(country='US', annual_gross='100000', tax_year='2026',
                  scenario=SCENARIO, region='FL', us_facts=json.dumps(facts('100000')))
    script = '''import io,json,sys
from urllib.parse import urlencode
from app.native_wsgi import application
status=[]
body=b''.join(application({'PATH_INFO':'/v1/tax/calculate','REQUEST_METHOD':'GET',
 'QUERY_STRING':urlencode(json.loads(sys.argv[1])),'wsgi.input':io.BytesIO(b'')},
 lambda code,headers:status.append(code)))
assert status[0].startswith('200'), status
print(body.decode())
'''
    env = dict(os.environ, PYTHONPATH=str(isolated),
               GPP_CACHE_DB=str(tmp_path/'unused-cache.sqlite3'),
               EARNWAGE_INSIGHTS_DB=str(tmp_path/'unused-insights.sqlite3'))
    completed = subprocess.run([sys.executable,'-c',script,json.dumps(params)],
                               cwd=isolated,env=env,capture_output=True,text=True,
                               check=True,timeout=30)
    result = json.loads(completed.stdout)
    assert result == calculate('US','100000',2026,SCENARIO,'FL',us_facts=facts('100000'))
    # Native WSGI bootstrap initializes its normal isolated fixture DBs.
    # The fiscal request must not insert cache entries or fiscal-rule tables.
    import sqlite3
    with sqlite3.connect(tmp_path/'unused-cache.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM cache').fetchone()[0] == 0
        tables = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert not {'tax_parameters','tax_rules'} & tables


@pytest.mark.parametrize('invalid', [
    {'sha256':'z'*64}, {'sha256':'0'*63}, {'sha256':None},
    {'bytes':0}, {'bytes':True}, {'tax_year':2025},
    {'url':'https://www.irs.gov/irb/2025-45_IRB'},
    {'scope':''}, {'scope':None}, {'status':403},
    {'verification_status':'acquired_not_reviewed'},
])
@pytest.mark.parametrize('state', ['TX', 'FL'])
def test_incomplete_or_unrelated_evidence_cannot_authorize_scoped_zero(monkeypatch,invalid,state):
    from app.us_tax_evidence import sources_for
    def corrupted(urls):
        return tuple(dict(source, **invalid) for source in sources_for(urls))
    monkeypatch.setattr('app.us_tax_jurisdictions.sources_for',corrupted)
    assert all(component['amount'] is None for component in coverage(state)['components'])
    result = calculate('US','100000',2026,SCENARIO,state,us_facts=facts('100000'))
    assert result['net_income'] is None and result['status']=='partial'
