"""Static regression checks for the public seven-language EarnWage website."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "website"
LANGUAGES = ("en", "pt", "es", "de", "fr", "it", "nl")


def catalog():
    content = (ROOT / "i18n.js").read_text(encoding="utf-8").strip()
    assert content.startswith("window.EarnWageI18n = ")
    return json.loads(content.removeprefix("window.EarnWageI18n = ").rstrip(";"))


def test_same_translation_keys_present_for_all_languages():
    values = catalog()
    assert tuple(values) == LANGUAGES
    expected = set(values["en"])
    assert "compareBtn" in expected and "pppWarn" in expected
    for lang in LANGUAGES:
        assert set(values[lang]) == expected
        assert all(isinstance(v, str) and v.strip() for v in values[lang].values())


def test_language_picker_header_and_saved_choice():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'id="languageSelector"' in html
    assert 'aria-labelledby="languageLabel"' in html
    assert 'src="./i18n.js"' in html
    assert html.index('id="languageSelector"') < html.index('</header>')
    assert 'localStorage.setItem("earnwage_lang"' in html
    assert 'document.documentElement.lang=' in html
    for lang in LANGUAGES:
        assert f'<option value="{lang}">' in html


def test_all_used_translation_keys_exist():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'ewT\("([A-Za-z0-9]+)"\)', html))
    block = html.split('const localizedTargets=[', 1)[1].split('];', 1)[0]
    used.update(re.findall(r',"([A-Za-z0-9]+)"\]', block))
    assert used <= set(catalog()["en"])
