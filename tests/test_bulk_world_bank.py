import json

import pytest

from app.bulk_core import BulkStore, digest
from app.bulk_world_bank import parse, run, url, PER_PAGE


def payload(value=100):
    return [{'page':1,'pages':1,'per_page':PER_PAGE,'total':1,'sourceid':'2','lastupdated':'2026-09-01'},
        [{'indicator':{'id':'NY.GDP.PCAP.CD'},'country':{'id':'PT'},'countryiso3code':'PRT',
          'date':'2024','unit':'','value':value,'obs_status':''}]]


def write(tmp_path,data):
    path=tmp_path/'wdi.json'
    path.write_text(json.dumps(data))
    return path


def test_published_wdi_decimals_and_all_countries(tmp_path):
    metadata,rows,missing=parse(write(tmp_path,payload(12345.67)),'gdp_per_capita',1)
    assert rows[0]['value']=='12345.67'
    assert rows[0]['original_country_code']=='PRT'
    assert rows[0]['unit']=='USD_current_per_person'
    assert missing==0
    assert 'PRT;ESP;DEU' in url('gdp_per_capita')


@pytest.mark.parametrize('value',[None])
def test_missing_never_zero(tmp_path,value):
    _,rows,missing=parse(write(tmp_path,payload(value)),'gdp_per_capita',1)
    assert rows==[] and missing==1


@pytest.mark.parametrize('field,value',[
    ('countryiso3code','XXX'),('date','May 2025'),('date','2024Q1'),('unit','EUR'),
    ('value',True),('value',-1),('value','100'),('obs_status','suppressed')])
def test_reject_unverified_dimensions(tmp_path,field,value):
    data=payload()
    data[1][0][field]=value
    with pytest.raises(ValueError):parse(write(tmp_path,data),'gdp_per_capita',1)


@pytest.mark.parametrize('field,value',[('page',2),('pages',2),('sourceid','1'),('total',2),('per_page',1)])
def test_pagination_schema_must_be_complete(tmp_path,field,value):
    data=payload()
    data[0][field]=value
    with pytest.raises(ValueError):parse(write(tmp_path,data),'gdp_per_capita',1)


def test_reject_other_indicator_and_country(tmp_path):
    data=payload()
    data[1][0]['indicator']['id']='wrong'
    with pytest.raises(ValueError):parse(write(tmp_path,data),'gdp_per_capita',1)
    data=payload()
    data[1][0]['country']['id']='ES'
    with pytest.raises(ValueError):parse(write(tmp_path,data),'gdp_per_capita',1)


def test_reject_duplicate_country_year(tmp_path):
    data=payload()
    data[1].append(dict(data[1][0]))
    data[0]['total']=2
    with pytest.raises(ValueError):parse(write(tmp_path,data),'gdp_per_capita',1)


def test_run_idempotent_and_failure_preserves(tmp_path):
    store=BulkStore(tmp_path/'staging.db')
    path=write(tmp_path,payload())
    class Fake:
        def get(self,requested,ttl=0):return path,{'url':requested,'sha256':digest(path)}
    assert run(store,Fake(),'gdp_per_capita')['accepted']==1
    assert run(store,Fake(),'gdp_per_capita')['resumed_rows']==1
    write(tmp_path,{'unexpected':'schema'})
    with pytest.raises(ValueError):run(store,Fake(),'gdp_per_capita')
    assert store.count()==1 and store.report()['runs'][-1]['status']=='failed'


def test_actual_two_page_contract_and_resume(tmp_path,monkeypatch):
    # Use a small page size to exercise genuine cross-page consistency.
    import app.bulk_world_bank as module
    monkeypatch.setattr(module,'PER_PAGE',1)
    files=[]
    for index,year in enumerate(('2023','2024'),1):
        data=payload(100+index)
        data[0].update(page=index,pages=2,per_page=1,total=2)
        data[1][0]['date']=year
        p=tmp_path/f'{index}.json'
        p.write_text(json.dumps(data));files.append(p)
    class Fake:
        def get(self,requested,ttl=0):
            p=files[1 if 'page=2' in requested else 0]
            return p,{'url':requested,'sha256':digest(p)}
    store=BulkStore(tmp_path/'staging.db')
    result=module.run(store,Fake(),'gdp_per_capita')
    assert result['pages']==2 and result['accepted']==2
    assert module.run(store,Fake(),'gdp_per_capita')['resumed_rows']==2


def test_reject_release_change_between_pages(tmp_path,monkeypatch):
    import app.bulk_world_bank as module
    monkeypatch.setattr(module,'PER_PAGE',1)
    class Fake:
        def get(self,requested,ttl=0):
            second='page=2' in requested
            data=payload()
            data[0].update(page=2 if second else 1,pages=2,per_page=1,total=2,
                           lastupdated='changed' if second else 'original')
            data[1][0]['date']='2024' if second else '2023'
            p=write(tmp_path,data)
            return p,{'url':requested,'sha256':digest(p)}
    store=BulkStore(tmp_path/'staging.db')
    with pytest.raises(ValueError):module.run(store,Fake(),'gdp_per_capita')
    assert store.report()['runs'][-1]['status']=='failed'


def test_complete_official_wdi_page(tmp_path):
    import gzip
    from pathlib import Path
    source=Path(__file__).parent/'fixtures/bulk/world_bank_gdp_per_capita.json.gz'
    target=tmp_path/'official.json'
    target.write_bytes(gzip.decompress(source.read_bytes()))
    metadata,rows,missing=parse(target,'gdp_per_capita',1)
    assert len(rows)==924 and missing==0
    assert len({r['country'] for r in rows})==14
    assert min(r['period'] for r in rows)=='1960'
    assert max(r['period'] for r in rows)=='2025'
    assert metadata['sourceid']=='2'


def test_null_period_provenance_and_cross_page_duplicates(tmp_path):
    registry={}
    seen=set()
    source=write(tmp_path,payload(None))
    parse(source,'gdp_per_capita',1,seen_rows=seen,missing_registry=registry)
    assert registry=={'PT':['2024']}
    with pytest.raises(ValueError):parse(source,'gdp_per_capita',1,seen_rows=seen)
