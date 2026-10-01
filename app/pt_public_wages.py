"""Portugal 2026 DGAEP civil-service starting basic remuneration benchmarks.

These are legally published PUBLIC career scale amounts, not occupation
market means, medians, typical take-home wages or private-sector estimates.
General-career references are CONDITIONAL (actual public recruitment into
that career and matching qualifications), not direct profession wages.
"""
SOURCE = "DGAEP — Sistema Remuneratório da Administração Pública 2026"
SOURCE_URL = "https://www.dgaep.gov.pt/srap/index.htm"
LEGAL_URL = "https://diariodarepublica.pt/dr/detalhe/decreto-lei/29-a-2026-1031110272"
TEACHER_URL = "https://www.dgae.medu.pt/web/14650/carreira-docente"
TEACHER_SCALE_URL = "https://www.spn.pt/Media/Default/Info/10000/400/70/1/SPN%20-%20Vencimento_%202026.pdf"
YEAR = "2026"
# Values are 2026 published monthly base, no supplements, paid months unassumed.
CAREERS = {
    "assistente_operacional": {
        "value": 934.99, "title": "Assistente operacional",
        "position": "1.ª posição", "level": "TRU 5", "source_url": SOURCE_URL,
    },
    "assistente_tecnico": {
        "value": 1035.63, "title": "Assistente técnico",
        "position": "1.ª posição", "level": "TRU 7", "source_url": SOURCE_URL,
    },
    "tecnico_superior": {
        "value": 1499.15, "title": "Técnico superior",
        "position": "1.ª posição", "level": "TRU 16", "source_url": SOURCE_URL,
    },
    "enfermeiro": {
        "value": 1657.04, "title": "Enfermeiro",
        "position": "1.ª posição", "level": "TRU 19", "source_url": SOURCE_URL,
    },
    "docente": {
        "value": 1770.69, "title": "Docente de educação pré-escolar, básica ou secundária (habilitado)",
        "position": "1.º escalão", "level": "Índice 167",
        "source_url": TEACHER_SCALE_URL,
    },
}

# Only literal matching occupation/career entries can use direct_public_career.
DIRECT = {
    "administrative_assistant": "assistente_tecnico",
    "nurse": "enfermeiro",
    "preschool_teacher": "docente",
    "secondary_teacher": "docente",
}
# Public-sector benchmark CONDITIONAL on appointment to an identified general
# career. No assertion that the named profession always belongs to that career.
CONDITIONAL = {
    "accountant": "tecnico_superior",
    "auditor": "tecnico_superior",
    "financial_analyst": "tecnico_superior",
    "software_developer": "tecnico_superior",
    "civil_engineer": "tecnico_superior",
    "mechanical_engineer": "tecnico_superior",
    "architect": "tecnico_superior",
    "data_analyst": "tecnico_superior",
    "psychologist": "tecnico_superior",
    "cybersecurity_specialist": "tecnico_superior",
    "teacher": "docente",
    "cleaner": "assistente_operacional",
    "construction_worker": "assistente_operacional",
    "healthcare_assistant": "assistente_operacional",
}
assert not set(DIRECT) & set(CONDITIONAL)


def wage(occupation):
    if occupation in DIRECT:
        category = DIRECT[occupation]
        mapping = "direct_public_career"
    elif occupation in CONDITIONAL:
        category = CONDITIONAL[occupation]
        mapping = "conditional_comparable_public_career"
    else:
        return {
            "status": "unavailable", "country": "PT",
            "occupation": occupation, "benchmark_type": "public_sector_entry",
            "reason": "No audited direct or explicitly conditional public career comparator",
        }
    row = CAREERS[category]
    warning = (
        "Reference only if recruitment is into this exact public career, "
        "with applicable qualifications and working-time regime; profession "
        "may also be employed in other public careers or the private sector."
        if mapping == "conditional_comparable_public_career"
        else "Direct public career benchmark conditional on actual appointment, "
        "qualification requirements and applicable employment regime."
    )
    return {
        "status": "available", "country": "PT", "occupation": occupation,
        "benchmark_type": "public_sector_entry",
        "mapping_precision": mapping,
        "value": row["value"], "currency": "EUR", "unit": "EUR/month",
        "measure": "published_entry_basic_remuneration",
        "reference_period": YEAR, "period": YEAR,
        "source": SOURCE, "source_url": row["source_url"],
        "legal_url": LEGAL_URL, "additional_source_url": TEACHER_URL if category == "docente" else None,
        "public_role": row["title"], "public_career": category,
        "entry_grade": row["position"], "entry_level": row["level"],
        "geography": "national_public_pay_scale",
        "observed_national_occupation_wage": False,
        "gross_basic_pay": True, "payment_count_assumed": False,
        "note": warning + " Monthly published base only: no allowances, bonuses, hours variation, regional supplements, tax or payment-count assumptions.",
    }


def coverage():
    from app.catalog import OCCUPATIONS
    return {
        "country": "PT", "status": "partial", "period": YEAR,
        "available_benchmarks": len(DIRECT) + len(CONDITIONAL),
        "direct_public_career": len(DIRECT),
        "conditional_comparable_public_career": len(CONDITIONAL),
        "total_occupations": len(OCCUPATIONS),
        "source": SOURCE, "source_url": SOURCE_URL,
        "precision": "official_public_sector_entry_not_occupation_market_wage",
        "note": "Separate layer, never added to exact occupation wage coverage.",
    }


def occupation_matrix():
    """40-entry PT audit: distinguish public matches from market wage coverage.

    Every available public amount is an explicit 2026 career benchmark. This
    matrix does not assert that national market wages exist for the job.
    """
    from app.catalog import OCCUPATIONS
    rows = []
    for job in OCCUPATIONS:
        observation = wage(job["id"])
        rows.append({
            "occupation": job["id"],
            "label_pt": job["translations"]["pt"],
            "public_benchmark_status": observation["status"],
            "mapping_precision": observation.get("mapping_precision"),
            "public_career": observation.get("public_role"),
            "value": observation.get("value"),
            "currency": observation.get("currency"),
            "reference_period": observation.get("reference_period"),
            "source_url": observation.get("source_url"),
            "notice": observation.get("note", observation.get("reason")),
        })
    return {
        "country": "PT", "total_occupations": len(rows), "period": YEAR,
        "market_wage_layer": "independent_not_inferred_from_public_pay",
        "direct_public_career": len(DIRECT),
        "conditional_comparable_public_career": len(CONDITIONAL),
        "public_benchmarks": len(DIRECT) + len(CONDITIONAL),
        "rows": rows,
    }


def public_sector_coverage():
    return {("PT", job): YEAR for job in set(DIRECT) | set(CONDITIONAL)}
