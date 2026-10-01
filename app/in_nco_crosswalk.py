"""Conservative EarnWage ↔ NCO-2015 three-digit *context* crosswalk.

Mapping is a semantic category association, NOT an occupation-level salary
equivalence. Official PLFS derivative groups are NCO-2015 three-digit groups;
they can contain multiple professions and specialties. Ambiguous titles
deliberately stay unmapped. Never feed this into exact occupation coverage.
Official classification: https://www.ncs.gov.in/documents/national%20classification%20of%20occupations%20_vol%20i-%202015.pdf
"""
from app.catalog import OCCUPATIONS
ALL_JOBS = {item["id"] for item in OCCUPATIONS}
from app.in_plfs_microdata import wages, coverage as nco_coverage

# Audit record: NCO group, verbatim classification label, why it is only context.
# Many-to-one associations (e.g. accountant / auditor / financial analyst) are
# intentional *context only*, not identical salary claims.
CONTEXT = {
    "accountant": ("241", "Finance Professionals"),
    "auditor": ("241", "Finance Professionals"),
    "financial_analyst": ("241", "Finance Professionals"),
    "doctor": ("221", "Medical Doctors"),
    "nurse": ("222", "Nursing and Midwifery Professionals"),
    "pharmacist": ("226", "Other Health Professionals"),
    "psychologist": ("263", "Social and Religious Professionals"),
    "physiotherapist": ("226", "Other Health Professionals"),
    "preschool_teacher": ("234", "Primary School and Early Childhood Teachers"),
    "software_developer": ("251", "Software and Application Developers and Analysts"),
    "it_technician": ("351", "Information and Communication Technology Operations and User Support Technicians"),
    "civil_engineer": ("214", "Engineering Professionals (Excluding Electrotechnology)"),
    "mechanical_engineer": ("214", "Engineering Professionals (Excluding Electrotechnology)"),
    "architect": ("216", "Architects, Planners, Surveyors and Designers"),
    "receptionist": ("422", "Client Information Workers"),
    "sales_assistant": ("522", "Shop Salespersons"),
    "truck_driver": ("833", "Heavy Truck and Bus Drivers"),
    "bus_driver": ("833", "Heavy Truck and Bus Drivers"),
    "electrician": ("741", "Electrical Equipment Installers and Repairers"),
    "plumber": ("712", "Building Finishers and Related Trades Workers"),
    "cook": ("512", "Cooks"),
    "waiter": ("513", "Waiters and Bartenders"),
    "cleaner": ("911", "Domestic, Hotel and Office Cleaners and Helpers"),
    "security_guard": ("541", "Protective Service Workers"),
    "lawyer": ("261", "Legal Professionals"),
    "dentist": ("226", "Other Health Professionals"),
    "healthcare_assistant": ("532", "Personal Care Workers in Health Services"),
    "cybersecurity_specialist": ("252", "Database and Network Professionals"),
    "secondary_teacher": ("233", "Secondary Education Teachers"),
    "welder": ("721", "Sheet and Structural Metal Workers, Moulders and Welders"),
    "automotive_mechanic": ("723", "Machinery Mechanics and Repairers"),
}
UNMAPPED = {
    "teacher": "Unspecified education level; multiple NCO teaching groups",
    "administrative_assistant": "Clerical, secretarial and administrative duties span NCO 411/412/334",
    "manager": "Generic manager; actual function determines NCO group",
    "supermarket_worker": "Shop sales, checkout, transport and stocking are different NCO groups",
    "construction_worker": "May be skilled builder or elementary construction labourer",
    "data_analyst": "May classify under statistics, software, or business analysis",
    "warehouse_operator": "May perform warehouse clerical, heavy-vehicle or elementary handling duties",
    "industrial_operator": "Machine/plant type determines NCO group",
    "agricultural_worker": "Skilled farming and elementary agricultural labour are distinct NCO groups",
}
SOURCE = "NCO-2015 three-digit classification; PLFS 2025 first-visit derivative"


def mapping(occupation):
    if occupation not in ALL_JOBS:
        raise ValueError("Unknown EarnWage occupation")
    if occupation in UNMAPPED:
        return {
            "status": "unmapped_ambiguous",
            "occupation": occupation,
            "precision": "broad_nco2015_three_digit_group",
            "reason": UNMAPPED[occupation],
            "exact_occupation_salary": False,
        }
    code, label = CONTEXT[occupation]
    return {
        "status": "broad_context_only", "occupation": occupation,
        "nco2015_group": code, "nco2015_group_label": label,
        "precision": "broad_nco2015_three_digit_group",
        "exact_occupation_salary": False,
        "warning": (
            "The group contains other occupations or specialties. "
            "This is a descriptive occupational-group mean, never the salary "
            "of the selected EarnWage profession."
        ),
        "classification_url": (
            "https://www.ncs.gov.in/documents/"
            "national%20classification%20of%20occupations%20_vol%20i-%202015.pdf"
        ),
    }


def context(occupation, state=None):
    item = mapping(occupation)
    if item["status"] != "broad_context_only":
        return item
    value = wages(item["nco2015_group"], state)
    if value["status"] == "unavailable":
        return {**item, "status": "group_observation_unavailable",
                "state_code": state,
                "reason": "No published disclosure-safe PLFS group observation for this geography"}
    if value["nco2015_label"] != item["nco2015_group_label"]:
        raise ValueError("NCO code-to-label mismatch; mapping requires renewed review")
    return {**item, "status": "available", "observation": value}


def coverage():
    available = {}
    for occupation in sorted(ALL_JOBS):
        try:
            item = context(occupation)
        except ValueError:
            raise
        available[occupation] = {
            "status": item["status"],
            "nco2015_group": item.get("nco2015_group"),
            "observation_available": item["status"] == "available",
        }
    return {
        "country": "IN", "total_occupations": len(ALL_JOBS),
        "mapped_to_broad_nco_groups": len(CONTEXT),
        "unmapped_ambiguous": len(UNMAPPED),
        "broad_group_observations_available": sum(
            item["observation_available"] for item in available.values()
        ),
        "exact_occupation_wages_from_this_mapping": 0,
        "underlying_nco_coverage": nco_coverage(),
        "by_occupation": available,
        "note": (
            "Broad group data and exact profession salaries have different "
            "precision and are never added together."
        ),
    }


# Fail loudly if catalogue changes and requires explicit mapping review.
assert not set(CONTEXT).intersection(UNMAPPED)
assert set(CONTEXT) | set(UNMAPPED) == ALL_JOBS
