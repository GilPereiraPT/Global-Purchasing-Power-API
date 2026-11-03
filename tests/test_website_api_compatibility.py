"""Version-compatible website integration: no false data inference or hidden official observations."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]/"website"

def test_older_api_ppp_observations_only_same_year():
    script=(ROOT/"ppp-fallback.js").read_text(encoding="utf-8")
    assert 'source!=="World Bank World Development Indicators"' in script
    assert 'local_currency_units_per_international_dollar' in script
    assert 'a.year!==b.year' in script
    assert 'original.status!=="not_implemented"' in script
    assert 'grossA*b.value/a.value' in script
    assert 'window.EarnWagePPP=Object.freeze({ensure})' in script
    for name in ("index.html","compare.html"):
        html=(ROOT/name).read_text(encoding="utf-8")
        assert 'src="./ppp-fallback.js"' in html
    assert 'window.EarnWagePPP.ensure' in (ROOT/"compare.js").read_text(encoding="utf-8")

def test_older_api_history_404_falls_back_to_actual_last_value_only():
    js=(ROOT/"history.js").read_text(encoding="utf-8")
    assert 'err?.message==="HTTP 404"' in js
    assert '"/v1/economy/compare?"' in js
    assert 'function renderLatestOnly(record)' in js
    assert 'Number.isInteger(record.year)' in js
    assert "if(b.year!==a.year+1)continue" in js
    labels=(ROOT/"history-i18n.js").read_text(encoding="utf-8")
    catalogue=json.loads(labels.removeprefix("window.EarnWageHistoryI18n=").strip().rstrip(";"))
    assert all(catalogue[k].get("latestOnly") for k in ("en","pt","es","de","fr","it","nl"))

def test_validated_north_american_wage_observations_visible():
    for name in ("explore.js","details.js"):
        js=(ROOT/name).read_text(encoding="utf-8")
        assert 'function preferredOccupationWage(record)' in js
        assert 'record.observations' in js
        assert 'x.measure==="median"' in js
        assert 'x.measure==="mean"' in js
        assert 'chosen.unit?.includes("/")' in js if name=="details.js" else 'selected.unit?.includes("/")' in js
    assert "group?.values?.local_currency" in (ROOT/"explore.js").read_text(encoding="utf-8")
