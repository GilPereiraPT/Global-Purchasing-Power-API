"""Static country political profile contracts (no network or production access)."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]/"website"
CODES={"PT","ES","DE","FR","GB","IE","NL","CH","IT","US","CA","BR","IN","PK"}
LANGS=("en","pt","es","de","fr","it","nl")

def test_country_page_includes_government_metadata_without_removing_previous_sections():
    html=(ROOT/"country.html").read_text(encoding="utf-8")
    for marker in ('id="countryPolitics"','id="countryCityTime"','id="detailsResults"','id="countryGuide"'):
        assert marker in html
    for item in ('country-politics.js','country-politics.css'):
        assert item in html

@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for JS contract test")
def test_14_profiles_and_seven_translations_are_well_formed():
    snippet=r"""
    const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
    const script=fs.readFileSync('website/country-politics.js','utf8');
    const context={window:{},document:{readyState:'loading',addEventListener(){}}};
    vm.runInNewContext(script,context,{timeout:1000});
    const data=context.window.EarnWagePoliticalProfiles;
    const codes=['PT','ES','DE','FR','GB','IE','NL','CH','IT','US','CA','BR','IN','PK'];
    assert.deepEqual(Object.keys(data.PROFILES).sort(),codes.sort());
    for(const [code,record] of Object.entries(data.PROFILES)){
      assert.ok(['republic','monarchy'].includes(record.form),code);
      assert.ok(['semi_presidential','parliamentary','presidential','collegial'].includes(record.system),code);
      assert.ok(['unitary','federal','autonomous_unitary','devolved_unitary','regionalised_unitary'].includes(record.territory),code);
      assert.equal(new URL(record.source).protocol,'https:',code);
      assert.ok(['2025','2026'].includes(record.reference),code);
      for(const locale of ['en','pt','es','de','fr','it','nl']){
        const l=data.labels[locale];
        assert.ok(l.title&&l[l.form?record.form:'form']&&l[record.form]&&l[record.system]&&l[record.territory],code+locale);
      }
    }
    assert.equal(data.PROFILES.PT.system,'semi_presidential');
    assert.equal(data.PROFILES.ES.form,'monarchy');
    assert.equal(data.PROFILES.CH.system,'collegial');
    assert.equal(data.PROFILES.US.territory,'federal');
    """
    subprocess.run(["node","-e",snippet],cwd=ROOT.parent,check=True,timeout=15)
