"""Publishing the EarnWage website must not change the API runtime."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"website"


def test_static_site_exists_and_has_all_country_profiles():
    html=list(SITE.glob("*.html"))
    assert len(html)==15
    assert (SITE/"index.html").exists()
    assert (SITE/"country-guides.js").exists()
    script=(SITE/"country-guides.js").read_text(encoding="utf-8")
    for code in ("PT","ES","DE","FR","GB","IE","NL","CH","IT","US","CA","BR","IN","PK"):
        assert '"'+code+'"' in script


def test_github_pages_workflow_keeps_existing_lab():
    yml=(ROOT/".github/workflows/earnwage-lab-pages.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in yml
    assert "cp -a website/. _site/" in yml
    assert "cp -a docs/. _site/lab/" in yml
    assert "actions/deploy-pages@v4" in yml
    assert "touch _site/.nojekyll" in yml
    assert "rm -f _site/_headers" in yml
    assert (ROOT/"docs/index.html").is_file()


def test_main_only_website_commit_does_not_trigger_api_runtime_deployment():
    deploy=(ROOT/".github/workflows/deploy-production.yml").read_text(encoding="utf-8")
    assert "!contains(github.event.workflow_run.head_commit.message, '[website-only]')" in deploy
    assert "vars.EARNWAGE_DEPLOY_ENABLED == 'true'" in deploy
    assert (SITE/"about.js").is_file()
    about=(SITE/"about.js").read_text(encoding="utf-8")
    assert 'location.hostname.endsWith(".github.io")' in about
    assert 'status("configured");return' in about
