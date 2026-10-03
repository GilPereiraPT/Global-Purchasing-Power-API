import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.bulk_core import Downloader, BulkStore, digest, valid_url

URL='https://api.worldbank.org/v2/test'


def artifact(store,tmp_path,content=b'official source'):
    p=tmp_path/'artifact'
    p.write_bytes(content)
    checksum=digest(p)
    store.artifact({'url':URL,'sha256':checksum})
    return checksum


def observation(value='100',period='2024'):
    return {'provider':'world_bank','dataset':'WDI:2:NY.GDP.PCAP.CD','country':'PT',
            'geography':'national','indicator':'gdp_per_capita','classification':None,
            'measure':'published_annual_indicator','unit':'USD_current_per_person','currency':None,
            'period':period,'value':value,'source_url':URL,'flags':''}


@pytest.mark.parametrize('url',['http://api.worldbank.org/x','https://evil.example/x',
    'https://user:secret@api.worldbank.org/x','https://api.worldbank.org:444/x'])
def test_provider_url_boundary(url):
    with pytest.raises(ValueError):valid_url(url)


def test_stream_cache_conditional_and_checksum(tmp_path):
    requests=[]
    def handler(request):
        requests.append(request)
        if len(requests)==2:
            assert request.headers['if-none-match']=='v1'
            return httpx.Response(304)
        return httpx.Response(200,content=b'{"value":1}',headers={'etag':'v1'})
    downloader=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(handler)),sleep=lambda _:None)
    path,first=downloader.get(URL)
    _,second=downloader.get(URL)
    assert second['cache_status']=='not_modified'
    downloader.get(URL,ttl=100)
    assert len(requests)==2
    path.write_bytes(b'corrupted')
    _,third=downloader.get(URL,ttl=100)
    assert len(requests)==3 and third['sha256']==first['sha256']
    assert 'if-none-match' not in requests[2].headers


@pytest.mark.parametrize('status',[429,500,502,503])
def test_transient_retry_backoff(tmp_path,status):
    calls=[]
    pauses=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(status if len(calls)<3 else 200,content=b'ok',headers={'Retry-After':'3'})
    downloader=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(handler)),sleep=pauses.append)
    downloader.get(URL)
    assert len(calls)==3 and pauses==[1,3,1,3,1]


@pytest.mark.parametrize('status',[401,403,404])
def test_no_auth_or_access_bypass(tmp_path,status):
    calls=[]
    def handler(r):
        calls.append(1)
        return httpx.Response(status)
    d=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(handler)),sleep=lambda _:None)
    with pytest.raises(httpx.HTTPStatusError):d.get(URL)
    assert len(calls)==1


@pytest.mark.parametrize('headers,content',[
    ({},b''),({},b'123456'),({'location':'https://unregistered.example/x'},b''),
    ({'retry-after':'120'},b'')])
def test_bounded_empty_redirect_and_long_retry(tmp_path,headers,content):
    status=302 if 'location' in headers else 429 if 'retry-after' in headers else 200
    d=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(status,headers=headers,content=content))),sleep=lambda _:None,max_bytes=5)
    with pytest.raises(ValueError):d.get(URL)
    assert not list(tmp_path.glob('*.part'))


def test_304_requires_trusted_cache(tmp_path):
    d=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(304))),sleep=lambda _:None)
    with pytest.raises(ValueError):d.get(URL)


def test_idempotent_import_versions_and_quarantine(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    assert store.ingest('job',sha,[observation()])['accepted']==1
    assert store.ingest('job',sha,[observation()])['resumed_rows']==1
    assert store.ingest('otherjob',sha,[observation()])['duplicates']==1
    revised=artifact(store,tmp_path,b'revised')
    assert store.ingest('revision',revised,[observation('110')])['accepted']==1
    suspicious=artifact(store,tmp_path,b'outlier')
    assert store.ingest('suspect',suspicious,[observation('900')])['quarantined']==1
    assert json.loads(store.db.execute('SELECT payload FROM bulk_current').fetchone()[0])['value']=='110'
    assert store.db.execute('SELECT COUNT(*) FROM bulk_versions').fetchone()[0]==3
    assert store.report()['quarantined_versions']==1


def test_resume_after_interrupted_batches(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    def interrupted():
        yield observation('100','2020')
        yield observation('110','2021')
        raise OSError('interrupted')
    with pytest.raises(OSError):store.ingest('job',sha,interrupted(),batch_size=2)
    assert store.count()==2
    counts=store.ingest('job',sha,[observation('100','2020'),observation('110','2021'),observation('120','2022')],batch_size=2)
    assert counts['resumed_rows']==2 and counts['accepted']==1 and store.count()==3


def test_failed_batch_is_atomic(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    with pytest.raises(ValueError):store.ingest('job',sha,[observation(),observation('NaN','2025')],batch_size=2)
    assert store.count()==0
    assert store.db.execute('SELECT COUNT(*) FROM bulk_progress').fetchone()[0]==0


@pytest.mark.parametrize('field,value',[('country','XX'),('geography','Lisbon'),('period','May 2025'),('value',True),('value','Infinity')])
def test_invalid_observation_never_stored(tmp_path,field,value):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    with pytest.raises(ValueError):store.ingest('job',sha,[dict(observation(),**{field:value})])
    assert store.count()==0


def test_quality_flags_quarantined(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    row=dict(observation(),provider='eurostat',flags='b')
    assert store.ingest('job',sha,[row])['quarantined']==1
    assert store.count()==0


def test_failed_refresh_preserves_previous_data(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    run=store.start('world_bank','gdp_per_capita')
    store.ingest('job',sha,[observation()])
    store.finish(run,'complete')
    failed=store.start('world_bank','gdp_per_capita')
    store.finish(failed,'failed','TimeoutError')
    report=store.report()
    assert report['accepted_observations']==1
    assert report['runs'][-1]['before_count']==report['runs'][-1]['after_count']==1
    assert report['runs'][-1]['status']=='failed'


def test_proxy_access_failure_not_retried(tmp_path):
    calls=[]
    def handler(request):
        calls.append(1)
        raise httpx.ProxyError('403 Forbidden')
    d=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(handler)),sleep=lambda _:None)
    with pytest.raises(httpx.ProxyError):d.get(URL)
    assert len(calls)==1


def test_transport_timeout_retried(tmp_path):
    calls=[]
    def handler(request):
        calls.append(1)
        if len(calls)==1:raise httpx.ReadTimeout('temporary')
        return httpx.Response(200,content=b'valid')
    d=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(handler)),sleep=lambda _:None)
    assert d.get(URL)[0].read_bytes()==b'valid'
    assert len(calls)==2


def test_quarantined_growth_does_not_freeze_entire_history(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    result=store.ingest('job',sha,[observation('100','2020'),observation('150','2021'),observation('160','2022')])
    assert result['quarantined']==1 and result['accepted']==2
    assert store.count()==2


def test_percentage_variation_uses_absolute_points_for_new_period(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    rows=[dict(observation('1','2020'),indicator='unemployment',unit='percent_of_labor_force'),
          dict(observation('2','2021'),indicator='unemployment',unit='percent_of_labor_force'),
          dict(observation('50','2022'),indicator='unemployment',unit='percent_of_labor_force')]
    counts=store.ingest('job',sha,rows)
    assert counts['accepted']==2 and counts['quarantined']==1


def test_reverse_chronological_history_still_checks_variation(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    sha=artifact(store,tmp_path)
    counts=store.ingest('job',sha,[observation('100','2022'),observation('900','2021')])
    assert counts['accepted']==1 and counts['quarantined']==1
