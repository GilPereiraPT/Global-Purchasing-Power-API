from copy import deepcopy

import pytest

from app.providers import UpstreamUnavailable, parse_eurostat


def payload():
    return {
        'id': ['geo', 'unit', 'coicop', 'time'], 'size': [1, 1, 1, 2],
        'dimension': {name: {'category': {'index': index}} for name, index in {
            'geo': {'PT': 0}, 'unit': {'I25': 0}, 'coicop': {'CP00': 0},
            'time': {'2025-01': 0, '2025-02': 1},
        }.items()},
        'value': {'0': 101.5, '1': 102.0},
    }


@pytest.mark.parametrize('dimension,code', [('geo', 'DE'), ('unit', 'RCH_M'), ('coicop', 'CP01')])
def test_rejects_wrong_geography_rate_or_category(dimension, code):
    data = payload()
    data['dimension'][dimension]['category']['index'] = {code: 0}
    with pytest.raises(UpstreamUnavailable):
        parse_eurostat(data, 'PT')


@pytest.mark.parametrize('dimension', ['sex', 'geo'])
def test_rejects_unexpected_or_duplicate_dimensions(dimension):
    data = payload()
    data['id'].append(dimension)
    data['size'].append(1)
    data['dimension'][dimension] = {'category': {'index': {'total': 0}}}
    with pytest.raises(UpstreamUnavailable):
        parse_eurostat(data, 'PT')


@pytest.mark.parametrize('frequency', ['M', 'A'])
def test_frequency_must_be_monthly(frequency):
    data = payload()
    data['id'].insert(0, 'freq')
    data['size'].insert(0, 1)
    data['dimension']['freq'] = {'category': {'index': {frequency: 0}}}
    if frequency == 'M':
        assert parse_eurostat(data, 'PT')[0] == {'period': '2025-01', 'index': 101.5}
    else:
        with pytest.raises(UpstreamUnavailable):
            parse_eurostat(data, 'PT')


def test_selects_requested_cells_instead_of_first_categories():
    data = payload()
    for name, index in [('geo', {'DE': 0, 'PT': 1}),
                        ('unit', {'RCH_M': 0, 'I15': 1}),
                        ('coicop', {'CP01': 0, 'CP00': 1})]:
        data['dimension'][name]['category']['index'] = index
        data['size'][data['id'].index(name)] = 2
    data['value'] = [999.0] * 14 + [101.5, 102.0]
    assert parse_eurostat(data, 'PT') == [
        {'period': '2025-01', 'index': 101.5}, {'period': '2025-02', 'index': 102.0}]


@pytest.mark.parametrize('case', ['sizes', 'offset', 'missing', 'period', 'nan'])
def test_malformed_data_fails_as_upstream_unavailable(case):
    data = deepcopy(payload())
    if case == 'sizes': data['size'] = [1]
    if case == 'offset': data['dimension']['geo']['category']['index']['PT'] = 1
    if case == 'missing': del data['dimension']['unit']
    if case == 'period': data['dimension']['time']['category']['index'] = {'2025': 0, '2026': 1}
    if case == 'nan': data['value']['0'] = float('nan')
    with pytest.raises(UpstreamUnavailable):
        parse_eurostat(data, 'PT')
