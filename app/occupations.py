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
