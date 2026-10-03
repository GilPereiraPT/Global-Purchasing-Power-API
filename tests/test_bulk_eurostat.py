import gzip
import json

import pytest

from app.bulk_eurostat import parse, run
from app.bulk_core import BulkStore, digest

HEADER='freq,na_item,ppp_cat,geo\\TIME_PERIOD\t2023 \t2024 \n'
ROW='A,PLI_EU27_2020,E011,PT\t85.1 \t86.2 p\n'


def write(tmp_path,text):
    path=tmp_path/'source.tsv.gz'
    path.write_bytes(gzip.compress(text.encode()))
    return path


def test_strict_selected_dimensions_and_flags(tmp_path):
    text=HEADER+ROW+'A,PLI_EU27_2020,E01,PT\t999\t999\n'+'A,PPP_EU27_2020,E011,PT\t1\t1\n'
    stats={}
    rows=list(parse(write(tmp_path,text),'household_price_level_eu27',stats))
    assert [r['value'] for r in rows]==['85.1','86.2']
    assert rows[1]['flags']=='p'
    assert rows[0]['original_dimensions']['ppp_cat']=='E011'
    assert stats['excluded_dimensions']==2


@pytest.mark.parametrize('header',[
    'freq,na_item,ppp_cat,geo,sex\\TIME_PERIOD\t2024\n',
    'freq,unit,ppp_cat,geo\\TIME_PERIOD\t2024\n',
    'freq,na_item,ppp_cat,geo\\TIME_PERIOD\t2024\t2024\n',
    'freq,na_item,ppp_cat,geo\\TIME_PERIOD\t2024Q1\n'])
def test_reject_unexpected_dimensions_periods(tmp_path,header):
    with pytest.raises(ValueError):list(parse(write(tmp_path,header),'household_price_level_eu27'))


@pytest.mark.parametrize('cell',['NaN','Infinity','1 q','-2','', '1.2.3'])
def test_reject_bad_cells(tmp_path,cell):
    text='freq,na_item,ppp_cat,geo\\TIME_PERIOD\t2024\nA,PLI_EU27_2020,E011,PT\t'+cell+'\n'
    with pytest.raises(ValueError):list(parse(write(tmp_path,text),'household_price_level_eu27'))


def test_suppression_missing_never_zero(tmp_path):
    stats={}
    rows=list(parse(write(tmp_path,HEADER+'A,PLI_EU27_2020,E011,PT\t: c\t99 c\n'),
                    'household_price_level_eu27',stats))
    assert rows==[] and stats['missing']==2


def test_duplicate_dimensions_rejected(tmp_path):
    with pytest.raises(ValueError):list(parse(write(tmp_path,HEADER+ROW+ROW),'household_price_level_eu27'))


def test_signature_and_expansion_bound(tmp_path):
    p=tmp_path/'bad'
    p.write_bytes(b'<html>upstream outage</html>')
    with pytest.raises(ValueError):list(parse(p,'household_price_level_eu27'))
    with pytest.raises(ValueError):list(parse(write(tmp_path,HEADER+ROW),'household_price_level_eu27',max_expanded=10))


def test_monthly_and_uk_source_distinction(tmp_path):
    text='freq,unit,coicop18,geo\\TIME_PERIOD\t2025M01\nM,RCH_A,TOTAL,PT\t-1.2\nM,RCH_A,TOTAL,UK\t4\n'
    rows=list(parse(write(tmp_path,text),'hicp_annual_change_monthly'))
    assert len(rows)==1 and rows[0]['period']=='2025-01' and rows[0]['value']=='-1.2'


def test_import_resume_preserves_history(tmp_path):
    path=write(tmp_path,HEADER+ROW)
    class Fake:
        def get(self,url,ttl=0):return path,{'url':url,'sha256':digest(path)}
    store=BulkStore(tmp_path/'staging.db')
    assert run(store,Fake(),'household_price_level_eu27')['accepted']==2
    assert run(store,Fake(),'household_price_level_eu27')['resumed_rows']==2
    assert store.count()==2
    versions=store.db.execute('SELECT payload FROM bulk_versions').fetchall()
    assert all('artifact_sha256' in json.loads(r[0]) for r in versions)


def test_live_bulk_hyphenated_month_format(tmp_path):
    text='freq,unit,coicop18,geo\\TIME_PERIOD\t1996-01\t2026-08\nM,RCH_A,TOTAL,PT\t2.1\t3.6\n'
    rows=list(parse(write(tmp_path,text),'hicp_annual_change_monthly'))
    assert [r['period'] for r in rows]==['1996-01','2026-08']
    assert rows[0]['original_period']=='1996-01'


def test_missing_selected_category_is_failure_not_success(tmp_path):
    text=HEADER+'A,PLI_EU27_2020,E01,PT\t1\t1\n'
    with pytest.raises(ValueError):list(parse(write(tmp_path,text),'household_price_level_eu27'))


@pytest.mark.parametrize('name,filename,period,value',[
    ('household_price_level_eu27','prc_ppp_ind_pt.tsv.gz','2024','87.0'),
    ('hicp_annual_change_monthly','prc_hicp_minr_pt.tsv.gz','2026-08','3.6'),
    ('net_annual_earnings_reference','earn_nt_net_pt.tsv.gz','2025','21449.05')])
def test_actual_official_verbatim_extracts(name,filename,period,value):
    from pathlib import Path
    root=Path(__file__).parent/'fixtures/bulk'
    rows=list(parse(root/filename,name))
    assert next(row for row in rows if row['period']==period)['value']==value
    assert all(row['country']=='PT' for row in rows)


def test_real_portuguese_earnings_break_is_not_silently_corrected():
    from pathlib import Path
    rows=list(parse(Path(__file__).parent/'fixtures/bulk/earn_nt_net_pt.tsv.gz','net_annual_earnings_reference'))
    row=next(r for r in rows if r['period']=='2024')
    assert row['value']=='1674.9' and row['flags']=='b'


def test_missing_observation_keeps_period_and_flags(tmp_path):
    stats={}
    list(parse(write(tmp_path,HEADER+'A,PLI_EU27_2020,E011,PT\t: c\t: \n'),'household_price_level_eu27',stats))
    assert stats['missing_periods_by_country']['PT']==[{'period':'2023','flags':'c'},{'period':'2024','flags':''}]
