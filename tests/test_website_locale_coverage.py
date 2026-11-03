"""Ensure every authored localized page string maps to a real translation key."""
import json
import re
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/"website"
GROUPS=(
    ("about-i18n.js", "EarnWageAboutI18n", "a", ("about",)),
    ("compare-i18n.js", "EarnWageCompareI18n", "c", ("compare",)),
    ("explore-i18n.js", "EarnWageExploreI18n", "t",
     ("salaries","countries","jobs","insights")),
    ("details-i18n.js", "EarnWageDetailsI18n", "d",
     ("methodology","sources","country","occupation")),
    ("history-i18n.js", "EarnWageHistoryI18n", "h",
     ("history","coverage")),
    ("wage-library-i18n.js", "EarnWageLibraryI18n", "w",
     ("wage-groups","source-directory")),
)


def test_all_page_localization_keys_are_backed_by_translations():
    for name, variable, attribute, pages in GROUPS:
        raw=(SITE/name).read_text(encoding="utf-8").strip()
        prefix="window."+variable+"="
        assert raw.startswith(prefix), name
        data=json.loads(raw.removeprefix(prefix).rstrip(";"))
        keys=set(data["en"])
        assert tuple(data)==("en","pt","es","de","fr","it","nl")
        for locale,translations in data.items():
            assert set(translations)==keys, (name,locale)
        for page in pages:
            html=(SITE/(page+".html")).read_text(encoding="utf-8")
            used=set(re.findall(r'data-'+attribute+r'="([a-zA-Z0-9]+)"',html))
            assert used <= keys, (page,used-keys)
