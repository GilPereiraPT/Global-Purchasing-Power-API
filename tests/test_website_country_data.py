"""Public country experience: actual observed 29-series data and country flags."""
from pathlib import Path
import json
import subprocess

SITE = Path(__file__).resolve().parents[1] / "website"
LANGS = ("en", "pt", "es", "de", "fr", "it", "nl")


def test_country_dashboard_uses_existing_public_country_indicators_endpoint():
    script = (SITE / "country-data.js").read_text(encoding="utf-8")
    assert '"/v1/countries/"+encodeURIComponent(code)+"/indicators"' in script
    assert '"/v1/countries/"+encodeURIComponent(code)+"/indicators/"+encodeURIComponent(key)+"?history=true"' in script
    assert 'data[i+1].year!==data[i].year+1' in script
    assert 'Number.isFinite(r.value)' in script
    assert 'source_url' in script
    assert 'ci-unavailable' in script
    assert 'container._ciGeneration!==generation' in script
    assert 'load on demand' in script


def test_all_40_country_indicators_and_7_locales_are_accounted_for():
    raw=(SITE/"country-data-i18n.js").read_text(encoding="utf-8").strip()
    prefix="window.EarnWageCountryDataLocale="
    assert raw.startswith(prefix)
    content=json.loads(raw[len(prefix):].rstrip(";"))
    assert tuple(content) == LANGS
    for language in LANGS:
        assert len(content[language]["metric"]) == 40
        assert content[language]["countryNote"].strip()
        assert all(label.strip() for label in content[language]["metric"].values())
        assert all(content[language][key] for key in (
            "economy", "employment", "health", "living", "education", "safety", "governance", "demography", "geography",
            "history", "historyMissing", "countryNote", "missing"))


def test_all_country_flags_and_groups_are_valid_in_node():
    source = r"""
    const assert=require('node:assert/strict'),fs=require('node:fs');
    const locales=fs.readFileSync('website/country-data-i18n.js','utf8');
    global.window={};
    eval(locales);
    eval(fs.readFileSync('website/country-data.js','utf8'));
    const data=window.EarnWageCountryData;
    const codes=['PT','ES','DE','FR','GB','IN','BR','PK','NL','CH','IT','IE','US','CA'];
    assert.equal(data.ALL.length,40);
    assert.equal(new Set(data.ALL).size,40);
    assert.equal(data.GROUPS.length,9);
    for(const code of codes){
      assert.equal([...data.flag(code)].length,2);
      assert.equal(data.flag(code),String.fromCodePoint(
        ...[...code].map(char=>127397+char.charCodeAt(0))));
    }
    for(const lang of ['en','pt','es','de','fr','it','nl'])
      for(const id of data.ALL)
        assert.ok(data.metricName(id,lang).length>2);
    """
    subprocess.run(["node", "-e", source], cwd=SITE.parent, check=True, timeout=15)


def test_primary_country_and_insights_pages_use_complete_dashboard():
    for page in ("country", "countries", "insights", "history"):
        html=(SITE/(page+".html")).read_text(encoding="utf-8")
        assert 'src="./country-data-i18n.js"' in html
        assert 'src="./country-data.js"' in html
        assert 'href="./country-data.css"' in html
        assert html.index('country-data-i18n.js') < html.index('country-data.js')
    details=(SITE/"details.js").read_text(encoding="utf-8")
    assert 'window.EarnWageCountryData.showCountry' in details
    explore=(SITE/"explore.js").read_text(encoding="utf-8")
    assert 'window.EarnWageCountryData.showCountry' in explore
    assert 'window.EarnWageCountryData.flagsGrid' in explore
    history=(SITE/"history.js").read_text(encoding="utf-8")
    assert 'renderIndicatorOptions' in history
    assert '"/v1/countries/"+encodeURIComponent($("country").value)+"/indicators/"' in history
    assert 'history=true' in history
    assert 'if(b.year!==a.year+1)continue' in history
    assert 'circle.append(tooltip)' in history
    assert 'circle.append(document.createElementNS' not in history


def test_flag_helper_used_in_main_country_selectors_and_no_external_flag_images():
    shell=(SITE/"site-shell.js").read_text(encoding="utf-8")
    assert 'window.EarnWageFlags=Object.freeze({flag,label:countryLabel})' in shell
    for page in ("index.html", "compare.js", "details.js", "explore.js", "history.js", "wage-library.js"):
        script=(SITE/page).read_text(encoding="utf-8")
        assert 'window.EarnWageFlags' in script
    assert "<img" not in (SITE/"country-data.js").read_text(encoding="utf-8")


def test_country_wage_guides_still_present_on_country_profile():
    html=(SITE/"country.html").read_text(encoding="utf-8")
    assert 'id="countryGuide"' in html
    assert 'id="detailsResults"' in html
    assert html.index('id="detailsResults"') < html.index('id="countryGuide"')
