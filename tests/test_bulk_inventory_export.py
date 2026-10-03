import json
import pytest
from app.bulk_inventory_export import compare,read_inventory


def row(**extra):
    return dict(provider='bls',dataset='OEWS',country='US',geography='national',
                indicator='occupational_salary',classification='SOC2018:15-1252',
                measure='mean',unit='USD/year',currency='USD',period='2025',value='100',**extra)


def export(tmp_path,rows,scope='complete'):
    p=tmp_path/'inventory.json';p.write_text(json.dumps(dict(schema='earnwage-observation-inventory-v1',scope=scope,exported_at='2026-10-03',observations=rows)));return p


def test_no_export_does_not_claim_new_coverage():
    assert compare([row()])['new'] is None


def test_duplicates_revisions_and_dimensions(tmp_path):
    p=export(tmp_path,[row()]);revised=row();revised['value']='101';regional=row();regional['geography']='BLS:2:01'
    assert compare([row()],p,authorization='owner-approved')['duplicates']==1
    assert compare([revised,regional],p,authorization='owner-approved')['revisions']==1
    assert compare([revised,regional],p,authorization='owner-approved')['new']==1
    dimension=row(dimensions={'industry':'123456'})
    assert compare([dimension],p,authorization='owner-approved')['new']==1


def test_authorization_and_duplicate_identity_required(tmp_path):
    p=export(tmp_path,[row(),row()])
    with pytest.raises(ValueError):read_inventory(p,authorization=None)
    with pytest.raises(ValueError):read_inventory(p,authorization='explicit')


@pytest.mark.parametrize('value',[True,'NaN','Infinity',{},'bogus'])
def test_invalid_values_rejected(tmp_path,value):
    r=row();r['value']=value
    with pytest.raises(ValueError):read_inventory(export(tmp_path,[r]),authorization='explicit')


def test_partial_scope_is_retained(tmp_path):
    assert compare([row()],export(tmp_path,[],scope='partial'),authorization='explicit')['scope']=='partial'


def test_aggregate_inventory_is_insufficient(tmp_path):
    p=tmp_path/'summary.json';p.write_text('{"total":10}')
    with pytest.raises(ValueError):read_inventory(p,authorization='explicit')


def test_symlink_rejected(tmp_path):
    p=export(tmp_path,[row()]);q=tmp_path/'link';q.symlink_to(p)
    with pytest.raises(ValueError):read_inventory(q,authorization='explicit')
