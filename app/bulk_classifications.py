"""Reuse reviewed national codes without manufacturing new equivalences.

Classification is not wage coverage. Shared/detailed codes can still describe
narrower or multiple professions. Group context is explicitly excluded from
individual wage admission. New mappings require source metadata and review.
"""
from app.catalog import COUNTRY_MAP, OCCUPATIONS
from app.north_america import US_SOC, CANADA_NOC
from app.uk_ashe_wages import SOC2020
from app.fr_insee_wages import APPROVED as FR
from app.nl_cbs_wages import APPROVED as NL
from app.br_cbo import CBO
from app.in_nco_crosswalk import CONTEXT

JOBS={job['id'] for job in OCCUPATIONS}
REGISTRY={
    'US':('SOC2018',US_SOC,'detailed_unit_existing_reviewed'),
    'CA':('NOC2021',CANADA_NOC,'unit_group_existing_reviewed'),
    'GB':('SOC2020',SOC2020,'unit_group_existing_reviewed'),
    'FR':('PCS-ESE',FR,'detailed_private_sector_existing_reviewed'),
    'NL':('BRC2014_ed2025',NL,'occupational_group_existing_reviewed'),
    'BR':('CBO2002',CBO,'six_digit_existing_reviewed'),
    'IN':('NCO2015',CONTEXT,'broad_group_context_only'),
}


def mapping(country,occupation):
    if country not in COUNTRY_MAP or occupation not in JOBS:raise ValueError('Unknown catalogue country or occupation')
    result={'country':country,'occupation':occupation,'code':None,'classification':None,
            'precision':None,'status':'no_reviewed_mapping_in_bulk_registry',
            'allows_individual_wage':False,'is_universal_one_to_one':False}
    entry=REGISTRY.get(country)
    if entry is None:return result
    system,rows,precision=entry
    original=rows.get(occupation)
    result.update(classification=system,precision=precision)
    if original is None:return result
    code=original['code'] if isinstance(original,dict) else original[0]
    result.update(code=code,status='existing_mapping_preserved',
                  allows_individual_wage=country!='IN')
    if country=='IN':result['status']='incompatible_group_context_for_individual_wages'
    result['note']='Existing mapping scope must match source release, population and salary definition; this is not a salary.'
    return result


def require_mapping(country,occupation,classification,code):
    approved=mapping(country,occupation)
    if not approved['allows_individual_wage'] or approved['classification']!=classification or approved['code']!=code:
        raise ValueError('Unreviewed or incompatible individual occupational classification')
    return approved


def catalogue():
    return [mapping(country,job) for country in COUNTRY_MAP for job in sorted(JOBS)]
