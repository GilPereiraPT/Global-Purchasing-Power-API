"""EarnWage occupation search dictionary: seven interface languages, stable job IDs.

Display translations are not automatically search terms: slash-form labels are
excluded unless a usable variant is explicitly curated. English is included
for every destination country because international adverts often use English.
"""
import re
import unicodedata
from app.catalog import OCCUPATIONS, COUNTRY_INTERFACE_LANGUAGES

LANGUAGES = ("pt", "en", "es", "de", "fr", "it", "nl")
EXTRA = {
    "software_developer": {
        "pt": ("programador", "programadora", "engenheiro de software", "engenheira de software", "desenvolvedor de software", "desenvolvedora de software"),
        "en": ("software engineer", "software developer", "programmer", "backend developer", "frontend developer", "full stack developer", "full-stack developer", "full stack engineer", "full-stack engineer", "fullstack engineer", "web developer", "python developer", "python engineer"),
        "es": ("desarrollador de software", "desarrolladora de software", "programador", "programadora", "ingeniero de software", "ingeniera de software"),
        "de": ("softwareentwickler", "softwareentwicklerin", "software engineer", "software-entwickler", "software-entwicklerin"),
        "fr": ("développeur logiciel", "développeuse logiciel", "ingénieur logiciel", "ingénieure logiciel", "développeur informatique", "développeuse informatique"),
        "it": ("sviluppatore software", "sviluppatrice software", "programmatore", "programmatrice", "ingegnere del software"),
        "nl": ("softwareontwikkelaar", "programmeur", "software engineer"),
    },
    "nurse": {"pt": ("enfermeiro", "enfermeira"), "en": ("registered nurse", "staff nurse", "nurse"),
              "es": ("enfermero", "enfermera"), "de": ("pflegefachkraft", "gesundheits- und krankenpfleger", "krankenpflegerin"),
              "fr": ("infirmier", "infirmière"), "it": ("infermiere", "infermiera"), "nl": ("verpleegkundige",)},
    "accountant": {"pt": ("contabilista", "técnico de contabilidade", "técnica de contabilidade"),
                   "en": ("accountant", "accounting specialist"),
                   "es": ("contable", "contador", "contadora"),
                   "de": ("buchhalter", "buchhalterin"), "fr": ("comptable",),
                   "it": ("contabile",), "nl": ("accountant", "boekhouder")},
    "electrician": {"pt": ("eletricista",), "en": ("electrician",),
                    "es": ("electricista",), "de": ("elektriker", "elektrikerin"),
                    "fr": ("électricien", "électricienne"), "it": ("elettricista",), "nl": ("elektricien",)},
    "truck_driver": {"pt": ("motorista de pesados", "motorista de camião"),
                     "en": ("truck driver", "hgv driver", "lorry driver"),
                     "es": ("conductor de camión", "conductora de camión"),
                     "de": ("lkw-fahrer", "lkw-fahrerin", "berufskraftfahrer"),
                     "fr": ("chauffeur poids lourd", "chauffeuse poids lourd", "conducteur poids lourd"),
                     "it": ("autista di camion", "camionista"), "nl": ("vrachtwagenchauffeur",)},
}
# Narrow, curated stem matching, not a blanket prefix wildcard.
STEMS = {
    "software_developer": {
        "en": ("software develop", "software engineer", "backend develop", "frontend develop"),
        "de": ("softwareentwickl",), "fr": ("développ",),
    }
}
CATALOG = {row["id"]: row for row in OCCUPATIONS}

def _clean(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()

def terms(occupation, country=None, provider=None):
    """Return deduplicated query terms; provider-specific behavior belongs in adapters."""
    row = CATALOG.get(occupation)
    if row is None or occupation == "manager":
        return ()
    languages = COUNTRY_INTERFACE_LANGUAGES.get(country, ["en"]) if country else LANGUAGES
    languages = tuple(dict.fromkeys((*languages, "en")))
    found = []
    for lang in languages:
        explicit = EXTRA.get(occupation, {}).get(lang, ())
        label = row["translations"].get(lang, "")
        aliases = row.get("aliases", {}).get(lang, ()) if occupation != "accountant" else ()
        candidates = (*explicit, *((label,) if "/" not in label else ()), *aliases)
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            candidate = candidate.strip()
            if candidate and _clean(candidate) not in {_clean(x) for x in found}:
                found.append(candidate)
    return tuple(found)

def matches(title, occupation):
    """Match whole title phrases; optional suffixes only on curated stems."""
    if not isinstance(title, str) or occupation not in CATALOG:
        return False
    normalized = _clean(title)
    for term in terms(occupation):
        needle = _clean(term)
        if re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", normalized):
            return True
    for variants in STEMS.get(occupation, {}).values():
        for stem in variants:
            if re.search(r"(?<!\w)" + re.escape(_clean(stem)) + r"[\w-]*(?!\w)", normalized):
                return True
    return False

def dictionary(occupation, country=None):
    row = CATALOG.get(occupation)
    if row is None:
        return None
    return {"occupation":occupation,"country":country,
            "languages":list(dict.fromkeys((*COUNTRY_INTERFACE_LANGUAGES.get(country,LANGUAGES),"en"))) if country else list(LANGUAGES),
            "terms":list(terms(occupation,country))}
