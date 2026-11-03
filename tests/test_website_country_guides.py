"""Smoke checks for fourteen source-aware EarnWage country-guide integrations."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"website"

def test_country_page_loads_data_guides():
    page=(ROOT/"country.html").read_text(encoding="utf-8")
    js=(ROOT/"details.js").read_text(encoding="utf-8")
    assert 'id="countryGuide"' in page
    assert 'src="./country-guides.js"' in page
    assert "EarnWageCountryGuides?.render" in js

def test_countries_page_has_links():
    page=(ROOT/"countries.html").read_text(encoding="utf-8")
    assert 'id="countryGuidesLinks"' in page
    assert 'src="./country-guides.js"' in page

def test_sources_and_source_categories_are_distinct():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    for country in ('"ES"','"IE"','"GB"','"FR"','"NL"','"CH"','"IT"','"US"','"CA"','"PT"','"DE"','"BR"','"IN"','"PK"'):
        assert country in code
    assert "es_ine_eaes" not in code  # no invented numeric series
    assert "ireland_public_sector_entry" in code
    assert "ireland_cso_occupational_group_context" in code
    assert "national_occupation_wage" in code
    assert "record?.status" in code
    assert "new Intl.NumberFormat" in code
    assert "http://www." not in code

def test_french_net_not_gross_and_no_tax_inference():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert "data.national_occupation_wage" in code
    assert "copy.frNet" in code
    assert "média LÍQUIDA mensal" in code
    assert "EQTP" in code

def test_dutch_hourly_median_and_release_status():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert "copy.nlGross" in code
    assert "wage?.publication_status" in code
    assert "2024–2025" in code
    assert "não se convertem valores horários" in code.lower() or "Não se convertem valores horários" in code

def test_swiss_group_is_context_and_publication_gated():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert "data.swiss_ch_isco19_submajor_context" in code
    assert "copy.swissPending" in code
    assert "CH-ISCO-19" in code
    assert "private staging" in code
    assert "copy.reported" in code

def test_italian_initial_salary_range_without_midpoint():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert "italianRangeCard" in code
    assert "record.min_value" in code and "record.max_value" in code
    assert "data.italy_cp2021_major_group_context" in code
    assert "group?.values?.[sex]" in code
    assert "copy.itContext" in code
    assert "não se calcula um ponto médio" in code

def test_us_canada_optional_regions_and_no_national_fallback():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert '["US","CA","DE","BR","IN"].includes(code)' in code
    assert 'params.set("region",region)' in code
    assert 'data.region?.ui?.visible' in code
    assert 'data.regional_occupation_wage' in code
    assert 'if(!observation)result.append(text("p",copy.regionMissing' in code
    assert 'copy.taxCaution' in code
    assert 'if(region&&["US","CA","DE","BR"].includes(code))compareParams.set("region_a",region)' in code

def test_us_state_and_canadian_province_statistic_units():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    for key in ('"a_median"','"a_mean"','"h_median"','"h_mean"','"median"','"mean"'):
        assert key in code
    for unit in ('"USD/year"','"USD/hour"','"CAD/year"','"CAD/hour"'):
        assert unit in code
    assert 'regionChooser.addEventListener("change"' in code
    assert "Federal" in code and "Québec" in code

def test_portugal_market_vs_public_2026_separate():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert "data.portugal_public_sector_entry" in code
    assert '"conditional_comparable_public_career"' in code
    assert "copy.ptPublicConditional" in code and "copy.ptMean" in code
    assert "Não se presumem 14 pagamentos" in code

def test_germany_brazil_region_source_specific_no_fallback():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert '["US","CA","DE","BR","IN"].includes(code)' in code
    assert "const obs=directRegional(regional)" in code
    assert "if(!obs)result.append(text(\"p\",copy.regionMissing" in code
    assert "copy.brComposite" in code
    assert "data.brazil_public_sector_entry" in code

def test_india_plfs_group_not_occupation():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    assert "india_plfs_employee_earnings_context" in code
    assert "india_nco2015_professional_group_context" in code
    assert "india_nco2015_regional_group_context" in code
    assert "function indianGroup(record)" in code
    assert "NÃO salários profissionais exatos" in code

def test_pakistan_group_source_and_catalogue_link():
    code=(ROOT/"country-guides.js").read_text(encoding="utf-8")
    lib=(ROOT/"wage-library.js").read_text(encoding="utf-8")
    assert 'copy.pkExact' in code and 'copy.pkGroupNote' in code
    assert 'wage-groups.html?country=PK' in code
    assert '["ES","PT","PK"].includes(requested)' in lib
    assert 'const requested=new URLSearchParams(location.search).get("country")' in lib
