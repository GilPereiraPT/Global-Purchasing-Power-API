"""City time comparison tests: exact instant and DST boundaries."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"website"

def test_country_profile_keeps_existing_sections_and_loads_comparison():
    html=(SITE/"country.html").read_text(encoding="utf-8")
    for marker in ('id="detailsResults"','id="countryGuide"','id="countryCityTime"',
                   'id="countryPolitics"','id="countryCityCompare"'):
        assert marker in html
    assert 'src="./city-time-compare.js"' in html
    assert 'href="./city-time-compare.css"' in html
    assert html.index('src="./city-timezones.js"')<html.index('src="./city-time-compare.js"')

@pytest.mark.skipif(shutil.which("node") is None,reason="Node not installed")
def test_timezone_differences_use_current_date_and_preserve_half_hour_offsets():
    source=r"""
    const assert=require('node:assert/strict');
    const fs=require('node:fs');
    const vm=require('node:vm');
    const ctx={
      window:{},
      document:{readyState:'loading',addEventListener(){}},
    };
    vm.runInNewContext(fs.readFileSync('website/city-timezones.js','utf8'),ctx);
    vm.runInNewContext(fs.readFileSync('website/city-time-compare.js','utf8'),ctx);
    const {offsetMinutes,cityLink}=ctx.window.EarnWageCityCompare;
    const winter=new Date('2026-01-15T12:00:00Z');
    const summer=new Date('2026-07-15T12:00:00Z');
    assert.equal(offsetMinutes('Europe/Lisbon',winter),0);
    assert.equal(offsetMinutes('Europe/Lisbon',summer),60);
    assert.equal(offsetMinutes('America/New_York',winter),-300);
    assert.equal(offsetMinutes('America/New_York',summer),-240);
    assert.equal(offsetMinutes('Asia/Kolkata',winter),330);
    assert.equal(offsetMinutes('Asia/Karachi',winter),300);
    assert.equal(offsetMinutes('Atlantic/Azores',winter),-60);
    assert.equal(offsetMinutes('Atlantic/Azores',summer),0);
    assert.equal(offsetMinutes('Pacific/Honolulu',summer),-600);
    assert.equal(offsetMinutes('Asia/Kolkata',winter)-offsetMinutes('Europe/Lisbon',winter),330);
    const map=cityLink({name:'Lisboa',code:'PT'},'pt');
    assert.ok(map.startsWith('https://www.openstreetmap.org/search?query='));
    assert.ok(decodeURIComponent(map).includes('Lisboa, Portugal'));
    for(const code of ['PT','ES','DE','FR','GB','IE','NL','CH','IT','US','CA','BR','IN','PK'])
      assert.ok(ctx.window.EarnWageCityTimezones[code].length>=3);
    """
    subprocess.run(["node","-e",source],cwd=ROOT,check=True,timeout=15)
