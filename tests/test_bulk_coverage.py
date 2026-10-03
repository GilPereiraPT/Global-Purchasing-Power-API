import hashlib
import json
import sqlite3

import pytest

from app.bulk_coverage import build_report, markdown, readonly
from app.bulk_catalogue import catalogue


def test_read_only_inventory_and_snapshot_distinction(tmp_path):
    snapshots=tmp_path/'snapshots'
    snapshots.mkdir()
    (snapshots/'north_america_wages.json').write_text(json.dumps({'records':[
        {'country':'CA','occupation':'nurse','classification':'NOC2021:31301','reference_period':'2023-2024','geography':'national','measure':'median','unit':'CAD/hour','source_url':'https://open.canada.ca'}]}))
    (snapshots/'groups.json').write_text(json.dumps({'observations':[
        {'country':'CH','isco08_major_group':'2','period':'2024','value':1}]}))
    dbpath=tmp_path/'wages.db'
    with sqlite3.connect(dbpath) as db:
        db.execute('CREATE TABLE north_america_wages(country,occupation,reference_period,geography,measure,unit)')
        db.execute("INSERT INTO north_america_wages VALUES ('US','nurse','May 2025','CA','mean','USD/year')")
    before=hashlib.sha256(dbpath.read_bytes()).hexdigest()
    report=build_report(dbpath,snapshot_dir=snapshots)
    assert report['country_count']==14 and report['occupation_pairs']==560
    assert hashlib.sha256(dbpath.read_bytes()).hexdigest()==before
    ca=next(c for c in report['countries'] if c['country']=='CA')
    nurse=next(o for o in ca['occupations'] if o['occupation']=='nurse')
    assert nurse['status']=='snapshot_not_imported'
    assert nurse['snapshot_periods']==['2023-2024']
    assert len(nurse['missing_target_years'])==11
    ch=next(c for c in report['countries'] if c['country']=='CH')
    assert ch['unmapped_or_group_snapshot_records']==1
    assert all(o['status']=='incompatible_classification_in_audited_source' for o in ch['occupations'])
    assert report['classification_mappings'][0]['original_code']=='NOC2021:31301'
    assert '| CA |' in markdown(report)
    with readonly(dbpath) as db:
        with pytest.raises(sqlite3.OperationalError):db.execute('CREATE TABLE unsafe(x)')


def test_missing_database_is_not_created(tmp_path):
    with pytest.raises(FileNotFoundError):build_report(tmp_path/'missing.db')
    assert not (tmp_path/'missing.db').exists()


def test_registry_covers_all_countries_without_invented_estimates():
    sources=catalogue()
    countries=set(c for s in sources for c in s['countries'])
    assert len(countries)==14
    assert all(s['useful_new_observations'] is None for s in sources)
    assert any(s['id']=='fso' and s['status']=='audited_group_only' for s in sources)


def test_committed_baseline_all_pairs_distinguishes_groups():
    report=build_report()
    assert report['occupation_pairs']==560
    assert report['summary']['snapshot_records']>7000
    assert report['summary']['stored_wage_observations']==0
    assert len(report['countries'])==14


def test_dashboard_has_all_pairs_and_escapes_data():
    from app.bulk_coverage import html_report
    report=build_report()
    report['countries'][0]['occupations'][0]['occupation']='<script>alert(1)</script>'
    page=html_report(report)
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page
    assert '<script>alert(1)</script>' not in page
    assert page.count('<tr>')==561
    assert 'aria-live="polite"' in page


def test_missing_upstream_and_quarantine_distinct_from_import_gap(tmp_path):
    snapshot_dir=tmp_path/'snapshots';snapshot_dir.mkdir()
    acquisition=tmp_path/'acquisition.json'
    acquisition.write_text(json.dumps({'runs':[{'provider':'world_bank','dataset':'gini','status':'complete',
        'result':{'missing_periods_by_country':{'PT':['2023']}}}],
        'quarantined_observations':[{'country':'PT','provider':'world_bank','indicator':'gini','period':'2024'}]}))
    report=build_report(snapshot_dir=snapshot_dir,acquisition_report=acquisition)
    pt=next(c for c in report['countries'] if c['country']=='PT')
    gini=next(i for i in pt['world_bank'] if i['indicator']=='gini')
    assert gini['upstream_missing_periods']==['2023']
    assert gini['quarantined_periods']==['2024']
    assert gini['observations']==0
