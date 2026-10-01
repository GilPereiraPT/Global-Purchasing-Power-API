"""Verified Indian PLFS 2025 employee-earnings context.

This is *not* an occupation-specific salary. The official 2025 PLFS
Statement 11 reports average preceding-calendar-month earnings of
regular wage/salaried workers in current weekly status (CWS). Keep
rural/urban and sex cells separate and never infer profession pay.
"""
SOURCE_URL = (
    "https://www.mospi.gov.in/uploads/publications_reports/"
    "publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_PLFS_2025_F_REV_29052026.pdf"
)
MICRODATA_URL = "https://microdata.gov.in/NADA/index.php/catalog/284"
LABOUR_BUREAU_URL = "https://www.labourbureau.gov.in/ows-1"
PERIOD = "January–December 2025"
UNIT = "INR/month"
# PLFS 2025 Annual Report, section 2.4.1, Statement 11, page 22.
# Layout: all-India; columns rural, urban and combined by male/female/person.
STATEMENT_11 = {
    "rural": {"male": 19300, "female": 13208, "person": 17841},
    "urban": {"male": 27973, "female": 21653, "person": 26247},
    "rural_urban": {"male": 24217, "female": 18353, "person": 22699},
}


def earnings():
    """Official broad labour-market average, intentionally not an exact-occupation wage."""
    return {
        "status": "available",
        "country": "IN",
        "geography": "national",
        "precision": "all_regular_wage_salaried_workers",
        "population": "regular wage/salaried employees in current weekly status",
        "employment_status": "regular_wage_salaried",
        "measure": "weighted_survey_average_monthly_earnings",
        "reference_period": PERIOD,
        "published_year": 2026,
        "currency": "INR",
        "unit": UNIT,
        "values": STATEMENT_11,
        "national_average": STATEMENT_11["rural_urban"]["person"],
        "source": "MoSPI, Periodic Labour Force Survey (PLFS) 2025, Statement 11",
        "source_url": SOURCE_URL,
        "note": (
            "All-occupation labour-market context only, not a salary for the "
            "selected profession or an individual offer; do not relabel as "
            "gross/net salary or multiply into an annual compensation estimate."
        ),
    }


def wage_sources():
    return {
        "country": "IN",
        "currency": "INR",
        "exact_occupation_wages": {
            "status": "pending_official_microdata_analysis",
            "reason": (
                "PLFS 2025 occupation-coded microdata require design-weighted "
                "analysis, verified NCO-2015 mapping, employment-status filtering, "
                "minimum sample-size checks and disclosure rules. "
                "No occupation salary has been inferred from national means."
            ),
            "classification": "NCO-2015",
            "source_url": MICRODATA_URL,
        },
        "plfs_2025": earnings(),
        "older_occupational_wage_survey": {
            "status": "historical_industry_scoped_not_current_national",
            "reference_period": "2016–2017 survey fieldwork",
            "source_url": LABOUR_BUREAU_URL,
            "note": (
                "Seventh-round Occupational Wage Survey targets selected organised "
                "industries and excludes much managerial, clerical and technical staff. "
                "Never treat its rates as current national occupation averages."
            ),
        },
        "regional_occupation_wages": {
            "status": "pending_official_microdata_analysis",
            "note": (
                "PLFS state/UT averages mix occupations; do not use them as "
                "profession-and-state wage observations."
            ),
        },
    }
