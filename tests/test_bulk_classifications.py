import pytest
from app.bulk_classifications import catalogue, mapping, require_mapping


def test_classification_registry_complete_but_not_salary_coverage():
    records=catalogue()
    assert len(records)==560
    assert all('value' not in r for r in records)
    assert all(not r['is_universal_one_to_one'] for r in records)
    assert mapping('US','nurse')['code']=='29-1141'
    assert mapping('BR','accountant')['code']=='252210'


def test_groups_cannot_be_promoted_to_profession():
    group=mapping('IN','nurse')
    assert group['code']=='222' and not group['allows_individual_wage']
    with pytest.raises(ValueError):require_mapping('IN','nurse','NCO2015','222')


@pytest.mark.parametrize('country,job,classification,code',[
    ('US','manager','SOC2018','11-0000'),('US','nurse','SOC2010','29-1141'),
    ('US','nurse','SOC2018','29-0000'),('CH','nurse','CH-ISCO19','22'),
    ('IT','nurse','CP2021','2')])
def test_wrong_version_broad_group_or_missing_mapping_rejected(country,job,classification,code):
    with pytest.raises(ValueError):require_mapping(country,job,classification,code)


def test_shared_codes_do_not_imply_same_individual_salary():
    assert mapping('CA','auditor')['code']==mapping('CA','accountant')['code']
    assert not mapping('CA','auditor')['is_universal_one_to_one']
    assert require_mapping('US','nurse','SOC2018','29-1141')['allows_individual_wage']
