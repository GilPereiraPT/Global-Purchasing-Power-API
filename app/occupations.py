"""Strict ISCO-08 mapping. None means no validated one-to-one mapping yet.
These codes are intentionally NOT guessed from the translated job title.
"""
ISCO08_EXACT = {
    "accountant": "2411",
    "nurse": "2221",
    "civil_engineer": "2142",
    "electrician": "7411",
    "software_developer": "2514",
    "cleaner": "9112",
    "dentist": "2261",
    "secondary_teacher": "2330",
    "welder": "7212",
    "automotive_mechanic": "7231",
    "agricultural_worker": None,
}
EXTRA_JOBS = [
    ("dentist", "Dentista", "Dentist"),
    ("healthcare_assistant", "Auxiliar de saúde", "Healthcare assistant"),
    ("data_analyst", "Analista de dados", "Data analyst"),
    ("cybersecurity_specialist", "Especialista em cibersegurança", "Cybersecurity specialist"),
    ("secondary_teacher", "Professor do ensino secundário", "Secondary school teacher"),
    ("warehouse_operator", "Operador de armazém", "Warehouse operator"),
    ("industrial_operator", "Operador industrial", "Industrial machine operator"),
    ("welder", "Soldador", "Welder"),
    ("automotive_mechanic", "Mecânico automóvel", "Automotive mechanic"),
    ("agricultural_worker", "Trabalhador agrícola", "Agricultural worker"),
]

# Curated BROAD ISCO-08 major-group placement for the 40 interface professions.
# This is not an exact 4-digit ISCO mapping and does not turn group earnings
# into an occupation-specific wage. Generic titles may span multiple subgroups.
ISCO08_MAJOR_GROUP = {
    "accountant": "2", "auditor": "2", "financial_analyst": "2",
    "doctor": "2", "nurse": "2", "pharmacist": "2", "psychologist": "2",
    "physiotherapist": "2", "teacher": "2", "preschool_teacher": "2",
    "software_developer": "2", "it_technician": "3",
    "civil_engineer": "2", "mechanical_engineer": "2", "architect": "2",
    "administrative_assistant": "4", "manager": "1", "receptionist": "4",
    "sales_assistant": "5", "supermarket_worker": "5",
    "truck_driver": "8", "bus_driver": "8", "electrician": "7",
    "plumber": "7", "construction_worker": "9", "cook": "5",
    "waiter": "5", "cleaner": "9", "security_guard": "5", "lawyer": "2",
    "dentist": "2", "healthcare_assistant": "5", "data_analyst": "2",
    "cybersecurity_specialist": "2", "secondary_teacher": "2",
    "warehouse_operator": "9", "industrial_operator": "8",
    "welder": "7", "automotive_mechanic": "7", "agricultural_worker": "9",
}
# Titles that may also belong to another group depending on actual duties.
ISCO08_MAJOR_GROUP_CAUTION = {
    "manager": "Generic manager title; classification depends on managerial duties.",
    "teacher": "Teaching level and role can affect the detailed ISCO code.",
    "supermarket_worker": "Checkout, sales, warehouse and management roles can differ.",
    "construction_worker": "Skilled trades and elementary construction work differ.",
    "warehouse_operator": "Warehouse clerks, forklift drivers and manual handlers differ.",
    "industrial_operator": "Machine type and duties determine the detailed occupation.",
    "agricultural_worker": "Skilled agriculture and elementary farm work differ.",
    "data_analyst": "Technical and professional data-analysis roles may differ.",
    "it_technician": "IT support and software engineering belong to different groups.",
}
