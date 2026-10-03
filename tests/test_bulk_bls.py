import zipfile
from pathlib import Path
import pytest
from openpyxl import Workbook
from app.bulk_bls import observations,url
from app.us_oews import IDENTITY_FIELDS,WAGE_FIELDS,workbook_records
from app.bulk_core import BulkStore


def release(tmp_path, rows=None, headers=None):
    headers=headers or list(IDENTITY_FIELDS+WAGE_FIELDS)
    wb=Workbook();ws=wb.active;ws.title='All May 2025 data';ws.append(headers)
    base=dict(AREA='99',AREA_TITLE='U.S.',AREA_TYPE='1',PRIM_STATE='US',NAICS='000000',
              NAICS_TITLE='Cross-industry',I_GROUP='cross-industry',OWN_CODE='1235',
              OCC_CODE='15-1252',OCC_TITLE='Software Developers',O_GROUP='detailed',
              **{f:100 if f.startswith('H_') else 200000 for f in WAGE_FIELDS})
    for extra in rows or [{}]:
        r={**base,**extra};ws.append([r.get(f) for f in headers])
    x=tmp_path/'source.xlsx';wb.save(x);z=tmp_path/'release.zip'
    with zipfile.ZipFile(z,'w') as a:a.write(x,'oesm25all/all_data_M_2025.xlsx')
    return z,x


def test_bulk_keeps_all_measures_original_period_and_suppression(tmp_path):
    z,x=release(tmp_path,[{'A_MEAN':'*','H_MEDIAN':'#'}]);stats={};rows=list(observations(z,2025,stats))
    assert len(rows)==12
    assert next(r for r in rows if r['measure']=='mean' and r['unit']=='USD/year')['value'] is None
    assert rows[0]['original_period']=='May 2025'
    assert rows[0]['classification']=='SOC2018:15-1252'
    assert stats['source_rows']==1 and stats['missing_wages']==2


def test_all_suppressed_rows_preserved_bulk_default_unchanged(tmp_path):
    z,x=release(tmp_path,[{f:'*' for f in WAGE_FIELDS}]);rows=list(observations(z,2025,{}))
    assert len(rows)==12 and all(r['value'] is None for r in rows)
    with pytest.raises(ValueError):list(workbook_records(x))


@pytest.mark.parametrize('area_type,area',[('2','01'),('3','72'),('4','12345'),('6','0100001')])
def test_regional_geography_not_national(tmp_path,area_type,area):
    z,_=release(tmp_path,[{'AREA_TYPE':area_type,'AREA':area,'AREA_TITLE':'Published area'}])
    assert all(r['geography']==f'BLS:{area_type}:{area}' for r in observations(z,2025,{}))


@pytest.mark.parametrize('bad',[{'AREA_TYPE':'5'},{'AREA':'XX'},{'A_MEAN':'not published'},{'OCC_CODE':'invalid'},{'AREA':'00'}])
def test_invalid_complete_source_rejected(tmp_path,bad):
    z,_=release(tmp_path,[bad])
    with pytest.raises(ValueError):list(observations(z,2025,{}))


def test_schema_and_archive_safety(tmp_path):
    z,_=release(tmp_path,headers=['OCC_CODE','OCC_TITLE','A_MEAN'])
    with pytest.raises(ValueError):list(observations(z,2025,{}))
    with zipfile.ZipFile(z,'w') as a:a.writestr('../unsafe.xlsx',b'bad')
    with pytest.raises(ValueError):list(observations(z,2025,{}))


def test_broad_groups_and_industries_do_not_expand_verified_mapping(tmp_path):
    z,_=release(tmp_path,[{'O_GROUP':'broad','OCC_CODE':'15-1200'},{'NAICS':'123456'},{}]);stats={}
    assert len(list(observations(z,2025,stats)))==12
    assert stats['source_rows']==3 and stats['excluded_rows']==2


def test_unvalidated_historical_classification_unavailable():
    with pytest.raises(ValueError):url(2020)


def test_missing_salary_ledger_and_resume(tmp_path):
    z,_=release(tmp_path,[{f:'*' for f in WAGE_FIELDS}]);s=BulkStore(tmp_path/'staging.sqlite3')
    checksum='a'*64;s.artifact({'sha256':checksum,'url':url(2025)})
    try:
        assert s.ingest('test',checksum,observations(z,2025,{}))['missing']==12
        assert s.count()==0 and s.report()['missing_versions']==12
        assert s.ingest('test',checksum,observations(z,2025,{}))['resumed_rows']==12
    finally:s.close()


def test_identical_source_duplicate_is_reported_without_double_counting(tmp_path):
    z,_=release(tmp_path,[{},{}]);stats={}
    assert len(list(observations(z,2025,stats)))==12
    assert stats['source_rows']==2 and stats['source_duplicate_rows']==1


def test_conflicting_source_duplicate_is_not_silently_a_revision(tmp_path):
    z,_=release(tmp_path,[{}, {'A_MEAN':250000}])
    with pytest.raises(ValueError):list(observations(z,2025,{}))


def test_authentic_downloaded_source_sample(tmp_path):
    import json
    data=json.loads((Path(__file__).parent/'fixtures/bulk/bls_2025_rows.json').read_text())
    z,_=release(tmp_path,data['rows'],data['headers'])
    rows=list(observations(z,2025,{}))
    assert len(rows)==24
    national=[r for r in rows if r['geography']=='national' and r['measure']=='mean' and r['unit']=='USD/year']
    assert national[0]['value']==str(float(data['rows'][0]['A_MEAN']))


def test_extra_dimensions_isolate_temporal_series(tmp_path):
    from app.bulk_core import observation_key
    z,_=release(tmp_path);row=next(observations(z,2025,{}));s=BulkStore(tmp_path/'stage.sqlite3')
    checksum='c'*64;s.artifact({'sha256':checksum,'url':url(2025)})
    try:
        other={**row,'value':'1','dimensions':{**row['dimensions'],'ownership':'1'}}
        assert observation_key(row)!=observation_key(other)
        assert s.ingest('dims',checksum,[row,other])['accepted']==2
    finally:s.close()


def test_published_missing_revision_does_not_leave_stale_current_salary(tmp_path):
    z,_=release(tmp_path);row=next(observations(z,2025,{}));s=BulkStore(tmp_path/'stage.sqlite3')
    try:
        for token,value in [('d',row['value']),('e',None),('f',row['value'])]:
            checksum=token*64;s.artifact({'sha256':checksum,'url':url(2025)})
            s.ingest(token,checksum,[{**row,'value':value}])
            assert s.count()==(0 if value is None else 1)
        assert s.db.execute('select count(*) from bulk_versions').fetchone()[0]==3
    finally:s.close()


def test_same_source_code_can_have_distinct_official_group_levels(tmp_path):
    z,_=release(tmp_path,[{'O_GROUP':'broad'},{}]);stats={}
    assert len(list(observations(z,2025,stats)))==12
    assert stats['excluded_rows']==1


def test_wrong_release_year_cannot_be_assigned_silently(tmp_path):
    z,_=release(tmp_path)
    with pytest.raises(ValueError):list(observations(z,2024,{}))
