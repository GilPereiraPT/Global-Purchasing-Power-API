"""The browser backfill must target exactly the official 16-series wave.

No network, cPanel access, or administrator token is needed for these tests.
"""
import json
import re
from pathlib import Path

from app.country_insights import INDICATOR_METADATA

HTML = Path(__file__).resolve().parent.parent / "docs" / "data-manager.html"


def test_wave_covers_catalogue_and_no_old_indicators():
    page = HTML.read_text(encoding="utf-8")
    match = re.search(r"const OPEN_DATA_WAVE=\s*(\[[\s\S]*?\]);", page)
    assert match is not None
    wave = json.loads(match.group(1))
    assert len(wave) == len(set(wave)) == 16
    assert set(wave) == set(INDICATOR_METADATA)


def test_wave_is_authenticated_serial_and_resumable():
    page = HTML.read_text(encoding="utf-8")
    assert 'id="waveCountry"' in page
    assert 'id="waveAll"' in page
    assert 'if(!metadata)' in page
    assert "new Set(metadata.indicators||[])" in page
    assert '$("mode").value="missing"' in page
    assert "startBatch(pairs,false,1000)" in page
    assert 'if(!gate.backups || gate.backups.length===0)' in page
    assert 'if(result==="empty")' in page
    assert "if(consecutiveFailures>=3)" in page
    assert 'if(stopped)break;' in page
    assert 'headers:{"Content-Type":"application/json","X-EarnWage-Admin-Token":token}' in page
