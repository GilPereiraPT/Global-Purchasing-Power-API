"""Brazil federal public-sector entry remuneration for EarnWage.

Only direct, audited equivalents are included. Values are the lowest/entry
point explicitly supported by federal remuneration legislation. This layer is
independent from RAIS observed occupation remuneration.
"""
SOURCE = "Governo Federal do Brasil - tabelas remuneratórias"
PORTAL_URL = "https://www.gov.br/servidor/pt-br/observatorio-de-pessoal-govbr/tabela-de-remuneracao-dos-servidores-publicos-federais-civis-e-dos-ex-territorios-1"
PERIOD = "2026-04"

ENTRIES = {
    "auditor": (22921.71, "Auditor-Fiscal da Receita Federal do Brasil", "Segunda", "I"),
    "accountant": (2769.57, "Contador", "A", "I"),
    "healthcare_assistant": (2182.59, "Auxiliar de Enfermagem", "A", "I"),
    "doctor": (9446.07, "Médico - jornada de 40 horas", "A", "I"),
    "nurse": (2377.53, "Enfermeiro", "A", "I"),
    "pharmacist": (2377.53, "Farmacêutico", "A", "I"),
    "psychologist": (2377.53, "Psicólogo", "A", "I"),
    "physiotherapist": (2377.53, "Fisioterapeuta", "A", "I"),
    "dentist": (2377.53, "Odontólogo", "A", "I"),
    "manager": (2377.53, "Administrador", "A", "I"),
    "administrative_assistant": (2182.59, "Agente Administrativo", "A", "I"),
    "architect": (5733.36, "Arquiteto", "A", "I"),
    "civil_engineer": (5733.36, "Engenheiro", "A", "I"),
    "mechanical_engineer": (5733.36, "Engenheiro", "A", "I"),
    "software_developer": (11150.80, "Analista em Tecnologia da Informação", "A", "I"),
    "it_technician": (11150.80, "Analista em Tecnologia da Informação", "A", "I"),
    "data_analyst": (11150.80, "Analista em Tecnologia da Informação", "A", "I"),
    "cybersecurity_specialist": (11150.80, "Analista em Tecnologia da Informação", "A", "I"),
    "teacher": (4326.60, "Magistério do Ensino Básico, Técnico e Tecnológico - 40 horas", "A", "1"),
    "secondary_teacher": (4326.60, "Magistério do Ensino Básico, Técnico e Tecnológico - 40 horas", "A", "1"),
}

def wage(occupation):
    row = ENTRIES.get(occupation)
    if row is None:
        return {"status":"unavailable","country":"BR","occupation":occupation,
                "benchmark_type":"public_sector_entry",
                "reason":"No audited direct federal public-sector equivalent yet"}
    value, title, grade, step = row
    return {
        "status":"available","country":"BR","occupation":occupation,
        "benchmark_type":"public_sector_entry",
        "value":value,"currency":"BRL","unit":"monthly",
        "reference_period":PERIOD,"period":PERIOD,
        "source":SOURCE,"source_url":PORTAL_URL,
        "public_role":title,"entry_grade":grade,"entry_step":step,
        "geography":"federal","nominal":True,
        "observed_national_occupation_wage":False,
        "note":"Federal public-sector entry benchmark; not a national occupation mean or median. Conditional bonuses and benefits are not inferred.",
    }

def public_sector_coverage():
    return {("BR", occupation): PERIOD for occupation in ENTRIES}
