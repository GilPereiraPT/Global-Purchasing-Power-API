"""Synthetic parser edge cases; never evidence of upstream salary acquisition."""
import copy
import hashlib
import json
from itertools import product

import pytest

from app import ch_bfs_wages as ch


def originals():
    categories = {
        'Jahr': {'2024': '2024', '2022': '2022'},
        'Grossregion': ch.REGIONS,
        'Berufsgruppe': {'25': '> 25 Spécialistes des technologies de l’information'},
        'Lebensalter': {'-1': 'Âge - total'},
        'Geschlecht': {'-1': 'Sexe - total'},
        ch.AXES[-1]: {k: v[0] for k, v in ch.PERCENTILES.items()},
    }
    meta = {'variables': [{'code': code, 'values': list(values), 'valueTexts': list(values.values())}
                          for code, values in categories.items()]}
    dims = {code: {'category': {'index': {key: i for i, key in enumerate(values)},
                               'label': values}} for code, values in categories.items()}
    dims['id'], dims['size'] = list(categories), [len(v) for v in categories.values()]
    cube = {'dataset': {'dimension': dims, 'source': 'OFS - Enquête suisse sur la structure des salaires - © OFS',
                        'value': [1000 + i for i, _ in enumerate(product(*categories.values()))], 'status': {}}}
    return meta, cube


def decode(meta, cube, *, mutate_provenance=False):
    mb, db, qb = [json.dumps(o).encode() for o in (meta, cube, ch.reviewed_query(meta))]
    prov = {'url': ch.API_URL, 'status': 200, 'acquired_at': '2026-10-04',
            **{k: hashlib.sha256(b).hexdigest() for k, b in
               [('metadata_sha256', mb), ('sha256', db), ('query_sha256', qb)]}}
    if mutate_provenance:
        prov['sha256'] = '0' * 64
    return ch.decode_snapshot(mb, db, qb, prov)


def test_all_published_years_regions_and_population_totals_preserved(tmp_path):
    meta, cube = originals()
    snapshot = decode(meta, cube)
    assert len(snapshot['observations']) == 80
    assert snapshot['publication_status'] == 'private_staging_only'
    assert snapshot['licence_status'] == 'redistribution_terms_not_verified'
    assert snapshot['currency'] == 'CHF' and snapshot['hours_per_week'] == 40
    path = tmp_path / 'stage.json'
    path.write_text(json.dumps(snapshot))
    national = ch.context('software_developer', path, period='2022')
    regional = ch.context('software_developer', path, period='2024', geography='CH:great_region:4')
    assert national['period'] == '2022' and national['value'] == 1040
    assert regional['geography'] == 'CH:great_region:4' and regional['value'] == 1020
    assert national['precision'] == 'ch_isco19_submajor_group'
    assert ch.context('software_developer', path, period='2023')['status'] == 'unavailable'
    assert ch.context('software_developer', path, geography='CH:unknown')['status'] == 'unavailable'


@pytest.mark.parametrize('flag,value', [('X', None), ('...', None), ('( )', 1000), (None, None)])
def test_missing_and_flagged_medians_do_not_create_coverage(tmp_path, flag, value):
    meta, cube = originals()
    cube['dataset']['value'][0] = value
    if flag:
        cube['dataset']['status']['0'] = flag
    snapshot = decode(meta, cube)
    path = tmp_path / 'stage.json'; path.write_text(json.dumps(snapshot))
    assert ch.context('software_developer', path, period='2024')['status'] == 'unavailable'
    assert snapshot['observations'][0]['value'] is None
    assert snapshot['observations'][0]['original_value'] == value
    snapshot['observations'] = [r for r in snapshot['observations'] if r['period'] == '2024']
    path.write_text(json.dumps(snapshot))
    assert ch.observed_coverage(path) == set()


@pytest.mark.parametrize('case', ['short_values', 'duplicate_index', 'unknown_flag', 'extra_dimension',
                                  'changed_label', 'suppressed_number', 'nan', 'false', 'checksum'])
def test_invalid_originals_fail_closed(case):
    meta, cube = originals()
    d = cube['dataset']
    if case == 'short_values': d['value'].pop()
    elif case == 'duplicate_index': d['dimension']['Grossregion']['category']['index']['1'] = 0
    elif case == 'unknown_flag': d['status']['0'] = '?'
    elif case == 'extra_dimension': d['dimension']['id'].append('Sector')
    elif case == 'changed_label': d['dimension']['Grossregion']['category']['label']['1'] = 'Unknown'
    elif case == 'suppressed_number': d['status']['0'] = 'X'
    elif case == 'nan': d['value'][0] = float('nan')
    elif case == 'false': d['value'][0] = False
    with pytest.raises(ValueError): decode(meta, cube, mutate_provenance=case == 'checksum')


def test_explicit_total_required_not_first_category():
    meta, _ = originals()
    meta['variables'][3]['values'] = ['1']
    meta['variables'][3]['valueTexts'] = ['Young employees']
    with pytest.raises(ValueError, match='total'): ch.reviewed_query(meta)


def test_duplicate_snapshot_observation_rejected(tmp_path):
    snapshot = decode(*originals()); snapshot['observations'].append(copy.deepcopy(snapshot['observations'][0]))
    path = tmp_path / 'stage.json'; path.write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match='duplicate'): ch.load_snapshot(path)


def test_private_staging_is_not_activated_at_default_runtime_path(tmp_path, monkeypatch):
    snapshot = decode(*originals())
    path = tmp_path / 'default.json'; path.write_text(json.dumps(snapshot))
    monkeypatch.setattr(ch, 'DEFAULT', path)
    assert ch.load_snapshot(path) == []
    assert ch.context('software_developer', path)['status'] == 'unavailable'
