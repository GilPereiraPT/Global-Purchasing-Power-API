import csv
import json
from pathlib import Path
import pytest
from app.bulk_job_bank import observations,validate_catalogue,LICENCE
from app.north_america import CANADA_URL
from app.bulk_core import BulkStore

FIXTURE=Path(__file__).parent/'fixtures/bulk/job_bank_2025.csv'


def test_authentic_national_provincial_economic_and_missing_sample():
    stats={};rows=list(observations(FIXTURE,stats))
    assert len(rows)==24 and stats['source_rows']==4
    assert {r['geography'] for r in rows}=={'national','CA:province:ON','CA:economic_region:ER3510','CA:economic_region:ER1020'}
    assert all(r['value'] is None for r in rows if r['period']=='unknown')
    assert all(r['original_period']=='2023-2024' for r in rows if r['geography']=='national')
    assert rows[0]['classification']=='NOC2021:21232'


def mutate(tmp_path,field,value):
    with FIXTURE.open() as f:r=list(csv.DictReader(f))
    r[0][field]=value;p=tmp_path/'bad.csv'
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=r[0]);w.writeheader();w.writerows(r)
    return p


@pytest.mark.parametrize('field,value',[('ER_Code_Code_RE','ER9999'),('prov','XX'),('ER_Name','Invented area'),('Annual_Wage_Flag_Salaire_annuel','2'),('NOC_Title_eng','Unrelated occupation'),('Reference_Period','current'),('Average_Wage_Salaire_Moyen','NaN'),('Median_Wage_Salaire_Median','-1')])
def test_schema_geography_units_and_values_fail_closed(tmp_path,field,value):
    with pytest.raises(ValueError):list(observations(mutate(tmp_path,field,value),{}))


def test_catalogue_licence_and_resource_verified(tmp_path):
    data={'success':True,'result':{'license_id':'ca-ogl-lgo','license_url':LICENCE,'metadata_modified':'2025-11-19','resources':[{'id':'9da94d63-b178-4a64-aeb3-b6a3bd721ad2','url':CANADA_URL,'format':'CSV'}]}}
    p=tmp_path/'metadata.json';p.write_text(json.dumps(data));assert validate_catalogue(p)=='2025-11-19'
    data['result']['resources'][0]['url']='https://example.org/data.csv';p.write_text(json.dumps(data))
    with pytest.raises(ValueError):validate_catalogue(p)
    data['result']['license_id']='unknown';p.write_text(json.dumps(data))
    with pytest.raises(ValueError):validate_catalogue(p)


def test_missing_period_is_preserved_not_invented(tmp_path):
    s=BulkStore(tmp_path/'stage.sqlite3');checksum='b'*64;s.artifact({'sha256':checksum,'url':CANADA_URL})
    try:
        counts=s.ingest('job_bank:sample',checksum,observations(FIXTURE,{}))
        assert counts['missing']>=6
        assert s.count()>0
        assert s.db.execute("select count(*) from bulk_versions where status='missing' and json_extract(payload,'$.original_period')='NA'").fetchone()[0]==6
    finally:s.close()


def test_public_blob_redirect_is_bounded_and_query_is_not_saved(tmp_path):
    import httpx
    from app.bulk_core import Downloader,valid_url
    destination='https://opencanada.blob.core.windows.net/opengovprod/resources/public.csv?sig=do-not-log'
    def handler(request):
        if request.url.host=='open.canada.ca':return httpx.Response(302,headers={'location':destination})
        return httpx.Response(200,content=b'official public csv')
    d=Downloader(tmp_path,httpx.Client(transport=httpx.MockTransport(handler)),sleep=lambda _:None)
    try:
        _,meta=d.get(CANADA_URL)
        assert 'sig=' not in meta['resolved_url']
        assert 'do-not-log' not in ''.join(p.read_text() for p in tmp_path.glob('*.json'))
        with pytest.raises(ValueError):valid_url('https://opencanada.blob.core.windows.net/private/container.csv')
    finally:d.close()
