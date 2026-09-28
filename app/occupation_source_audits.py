"""Audited official occupation-wage sources that are not exact enough for EarnWage.

These records are deliberately descriptive.  They must never be loaded into
exact occupation wage tables unless a future official publication reaches the
required occupation precision.
"""

AUDIT_DATE = "2026-09-28"

OCCUPATION_SOURCE_AUDITS = {
    "CH": {
        "country": "CH",
        "status": "official_group_data_only",
        "exact_occupation_accepted": False,
        "source": "Swiss Federal Statistical Office (FSO), Earnings Structure Survey (ESS) 2024",
        "source_url": (
            "https://www.pxweb-admin-a.bfs.admin.ch/pxweb/en/"
            "px-x-0304010000_205/-/px-x-0304010000_205.px/"
        ),
        "published_measure": "standardised gross monthly wage; median and percentiles; CHF",
        "occupation_classification": "CH-ISCO-19",
        "published_precision": "major and sub-major occupation groups (1-2 digits)",
        "rejection_reason": (
            "Published wage table stops at CH-ISCO-19 1-2 digit groups; "
            "EarnWage exact occupation coverage requires a defensible individual "
            "occupation mapping and must not inherit a broad-group wage."
        ),
        "ilostat_rows_audited": 2340,
        "ilostat_exact_isco08_4digit_rows": 0,
        "audit_date": AUDIT_DATE,
    },
    "IT": {
        "country": "IT",
        "status": "official_group_data_only",
        "exact_occupation_accepted": False,
        "source": "Istat, Rilevazione sulla struttura delle retribuzioni (RCL-SES) 2022",
        "source_url": (
            "https://www.istat.it/comunicato-stampa/"
            "la-struttura-delle-retribuzioni-in-italia-anno-2022/"
        ),
        "published_measure": "gross hourly and annual earnings; EUR",
        "occupation_classification": "CP2021 aligned with ISCO-08",
        "published_precision": "broad professional groups in published wage tables",
        "rejection_reason": (
            "Official Tav.4/Tav.9 wage tables publish broad professional groups, "
            "not individual occupations such as nurse, accountant or software "
            "developer; broad groups cannot be counted as exact EarnWage pairs."
        ),
        "ilostat_rows_audited": 1584,
        "ilostat_exact_isco08_4digit_rows": 0,
        "audit_date": AUDIT_DATE,
    },
}


def source_audit(country):
    """Return a copy so callers cannot mutate the registry."""
    item = OCCUPATION_SOURCE_AUDITS.get(str(country).upper())
    if item is None:
        return {"status": "not_audited"}
    return dict(item)
