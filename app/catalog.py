"""Versioned country and occupation catalogue. National salaries are NOT capital salaries."""
COUNTRIES = [
    ("PT", "Portugal", "Lisbon", "EUR", "eurostat"),
    ("ES", "Spain", "Madrid", "EUR", "eurostat"),
    ("DE", "Germany", "Berlin", "EUR", "eurostat"),
    ("FR", "France", "Paris", "EUR", "eurostat"),
    ("GB", "United Kingdom", "London", "GBP", "eurostat"),
    ("IN", "India", "New Delhi", "INR", None),
    ("BR", "Brazil", "Brasília", "BRL", None),
    ("PK", "Pakistan", "Islamabad", "PKR", None),
    ("NL", "Netherlands", "Amsterdam", "EUR", "eurostat"),
    ("CH", "Switzerland", "Bern", "CHF", "eurostat"),
    ("IT", "Italy", "Rome", "EUR", "eurostat"),
    ("IE", "Ireland", "Dublin", "EUR", "eurostat"),
]
COUNTRY_MAP = {
    code: {"code": code, "name": name, "capital": capital, "currency": currency,
           "inflation_provider": provider, "capital_cost_of_living": "unavailable",
           "occupation_salary": "unavailable"}
    for code, name, capital, currency, provider in COUNTRIES
}
# Stable identifiers; map to more specific ISCO/ESCO records only after validation.
JOBS = [
    ("accountant", "Contabilista", "Accountant"),
    ("auditor", "Auditor", "Auditor"),
    ("financial_analyst", "Analista financeiro", "Financial analyst"),
    ("doctor", "Médico", "Doctor"),
    ("nurse", "Enfermeiro", "Nurse"),
    ("pharmacist", "Farmacêutico", "Pharmacist"),
    ("psychologist", "Psicólogo", "Psychologist"),
    ("physiotherapist", "Fisioterapeuta", "Physiotherapist"),
    ("teacher", "Professor", "Teacher"),
    ("preschool_teacher", "Educador de infância", "Preschool teacher"),
    ("software_developer", "Programador", "Software developer"),
    ("it_technician", "Técnico de informática", "IT technician"),
    ("civil_engineer", "Engenheiro civil", "Civil engineer"),
    ("mechanical_engineer", "Engenheiro mecânico", "Mechanical engineer"),
    ("architect", "Arquiteto", "Architect"),
    ("administrative_assistant", "Assistente administrativo", "Administrative assistant"),
    ("manager", "Gestor", "Manager"),
    ("receptionist", "Rececionista", "Receptionist"),
    ("sales_assistant", "Vendedor", "Sales assistant"),
    ("supermarket_worker", "Operador de supermercado", "Supermarket worker"),
    ("truck_driver", "Motorista de pesados", "Truck driver"),
    ("bus_driver", "Motorista de autocarro", "Bus driver"),
    ("electrician", "Eletricista", "Electrician"),
    ("plumber", "Canalizador", "Plumber"),
    ("construction_worker", "Trabalhador da construção", "Construction worker"),
    ("cook", "Cozinheiro", "Cook"),
    ("waiter", "Empregado de mesa", "Waiter"),
    ("cleaner", "Empregado de limpeza", "Cleaner"),
    ("security_guard", "Segurança privado", "Security guard"),
    ("lawyer", "Advogado", "Lawyer"),
]
from app.occupations import EXTRA_JOBS, ISCO08_EXACT

JOBS.extend(EXTRA_JOBS)
OCCUPATIONS = [
    {"id": key, "isco08": ISCO08_EXACT.get(key),
     "translations": {"pt": pt, "en": en}} for key, pt, en in JOBS
]
assert len(OCCUPATIONS) == 40

