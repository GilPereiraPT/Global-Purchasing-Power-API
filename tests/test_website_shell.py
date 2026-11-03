"""Cross-page layout, navigation, accessibility and language checks."""
from pathlib import Path
import shutil
import subprocess

SITE = Path(__file__).resolve().parents[1] / "website"
PAGES = (
    "index", "compare", "salaries", "countries", "jobs", "insights",
    "about", "methodology", "sources", "country", "occupation",
    "history", "coverage", "wage-groups", "source-directory",
)
LANGUAGES = ("en", "pt", "es", "de", "fr", "it", "nl")


def test_every_public_page_uses_common_shell():
    for page in PAGES:
        content = (SITE / f"{page}.html").read_text(encoding="utf-8")
        assert 'href="./site-shell.css"' in content, page
        assert 'src="./site-shell.js"' in content, page
        assert content.index("site-shell.css") < content.index("</head>"), page
        assert content.index("site-shell.js") > content.index("</footer>"), page
        assert '<main' in content and '</main>' in content, page
        assert '<header' in content and '<footer' in content, page


def test_shell_has_single_source_of_truth_for_navigation():
    js = (SITE / "site-shell.js").read_text(encoding="utf-8")
    for page in PAGES:
        assert page + ".html" in js, page
    for language in LANGUAGES:
        assert language + ":{" in js, language
    for anchor in ('"history.html"', '"coverage.html"',
                   '"source-directory.html"', '"sources.html"',
                   '"methodology.html"', '"about.html"'):
        assert anchor in js
    assert 'aria-current' in js
    assert 'localStorage.getItem("earnwage_lang")' in js
    assert 'localStorage.setItem' not in js  # The page owns language preference.
    assert 'document.querySelector("header nav")' in js
    assert 'document.querySelector("footer")' in js


def test_keyboard_and_mobile_accessibility_basics():
    js = (SITE / "site-shell.js").read_text(encoding="utf-8")
    css = (SITE / "site-shell.css").read_text(encoding="utf-8")
    assert "ew-skip-link" in js and 'skip:"' in js
    assert 'event.key==="Escape"' in js
    assert 'summary' in js and 'aria-label' in js
    assert 'prefers-reduced-motion:reduce' in css
    assert ':focus-visible' in css
    assert 'overflow-x:auto' in css
    assert 'max-width:960px' in css


def test_homepage_does_not_translate_nav_links_by_position():
    home = (SITE / "index.html").read_text(encoding="utf-8")
    assert '".navlinks a:nth-child(' not in home
    # Those former footer IDs are intentionally removed by the shared shell.
    for identifier in ('aboutLink', 'methodologyLink', 'sourcesLink'):
        assert f'$("{identifier}")' not in home


def test_javascript_can_be_syntax_checked_when_node_is_available():
    node = shutil.which("node")
    if node is None:
        return
    for path in (
        "site-shell.js", "explore.js", "details.js", "history.js",
        "wage-library.js", "compare.js", "about.js",
    ):
        result = subprocess.run(
            [node, "--check", str(SITE / path)],
            capture_output=True, text=True, timeout=10, check=False,
        )
        assert result.returncode == 0, f"{path}: {result.stderr}"
