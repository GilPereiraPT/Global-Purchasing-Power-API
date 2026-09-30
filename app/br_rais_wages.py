"""Brazil RAIS 2025 occupation-specific remuneration snapshot.

Values are medians of December 2025 remuneration for active formal employment
links on 31/12/2025 with contracted weekly hours of 40-44, grouped by six-digit
CBO 2002 occupation. 99K publishes reproducible aggregates derived from the
official MTE RAIS 2025 microdata. This layer is occupation-specific and must
never be replaced by a broad occupational-group average.
"""
from app import br_cbo

SOURCE = "RAIS 2025 - Ministério do Trabalho e Emprego"
SOURCE_URL = "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2025/rais-2025"
AGGREGATOR = "99K - agregação dos microdados RAIS 2025"
PERIOD = "2025-12"
PRECISION = "occupation_cbo2002_6_digit"
POPULATION = "active formal employment links on 31/12/2025, contracted 40-44 hours/week"

# occupation: (median BRL/month, employment links, evidence slug)
OBSERVATIONS = {
    "accountant": (5749, 145518, "contador"),
    "financial_analyst": (5003, 79895, "analista-financeiro-instituicoes-financeiras"),
    "teacher": (5560, 414687, "professor-de-nivel-superior-do-ensino-fundamental-primeira-a-quarta-serie"),
    "preschool_teacher": (4985, 88125, "professor-de-nivel-superior-na-educacao-infantil-quatro-a-seis-anos"),
    "warehouse_operator": (2113, 167148, "armazenista"),
    "agricultural_worker": (2103, 309909, "trabalhador-agropecuario-em-geral"),
    "auditor": (12612, 31392, "auditor-contadores-e-afins"),
    "doctor": (13201, 67274, "medico-clinico"),
    "nurse": (6195, 236101, "enfermeiro"),
    "pharmacist": (5604, 131945, "farmaceutico"),
    "psychologist": (5262, 36791, "psicologo-clinico"),
    "physiotherapist": (4096, 24995, "fisioterapeuta-geral"),
    "software_developer": (9547, 255957, "analista-de-desenvolvimento-de-sistemas"),
    "civil_engineer": (12032, 47964, "engenheiro-civil"),
    "mechanical_engineer": (14506, 14242, "engenheiro-mecanico"),
    "architect": (11017, 9610, "arquiteto-de-edificacoes"),
    "administrative_assistant": (2859, 2048564, "assistente-administrativo"),
    "receptionist": (1920, 477787, "recepcionista-em-geral"),
    "truck_driver": (3413, 974526, "motorista-de-caminhao-rotas-regionais-e-internacionais"),
    "electrician": (3068, 106544, "eletricista-de-instalacoes"),
    "cook": (2131, 465253, "cozinheiro-geral"),
    "waiter": (2190, 161339, "garcom"),
    "cleaner": (1851, 1569330, "faxineiro"),
    "security_guard": (2783, 495656, "vigilante"),
    "lawyer": (6618, 48389, "advogado"),
    "dentist": (7313, 32948, "cirurgiao-dentista-clinico-geral"),
    "welder": (3781, 178882, "soldador"),
    "automotive_mechanic": (2575, 188658, "mecanico-de-manutencao-de-automoveis-motocicletas-e-veiculos-similares"),
}

def wages(country, occupation):
    if country != "BR":
        return {"status":"unavailable","country":country,"occupation":occupation,
                "reason":"RAIS CBO integration applies only to Brazil"}
    row = OBSERVATIONS.get(occupation)
    cbo = br_cbo.CBO.get(occupation)
    if row is None or cbo is None:
        return {"status":"unavailable","country":"BR","occupation":occupation,
                "geography":"national",
                "reason":"No validated six-digit CBO RAIS 2025 occupation observation"}
    value, links, slug = row
    return {
        "status":"available","country":"BR","occupation":occupation,
        "geography":"national","period":PERIOD,"reference_period":PERIOD,
        "value":value,"currency":"BRL",
        "unit":"monthly remuneration, December 2025",
        "source_unit":"BRL/month","measure":"median",
        "salary_concept":"december_remuneration",
        "source":SOURCE,"source_url":SOURCE_URL,
        "derived_aggregation":AGGREGATOR,
        "evidence_url":"https://99k.com.br/carreiras/"+slug,
        "cbo_code":cbo["code"],"source_label":cbo["title"],
        "employment_links":links,"population":POPULATION,
        "precision":PRECISION,
        "nominal":True,
        "note":"Occupation-specific RAIS 2025 aggregate. Formal employment only; self-employed, PJ and informal work are excluded.",
    }

def observed_coverage():
    return {("BR", occupation): PERIOD for occupation in OBSERVATIONS}
