"""Brazil CBO 2002 occupation mapping for EarnWage.

CBO is the official occupational classification used by RAIS/CAGED.
Mappings here are occupation-level (six-digit) whenever EarnWage has a
defensible direct Brazilian occupation. Salary observations must be loaded
separately from RAIS and must never be inferred from the CBO mapping itself.
"""
SOURCE="Ministério do Trabalho e Emprego - Classificação Brasileira de Ocupações (CBO 2002)"
SOURCE_URL="https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/cbo/servicos/downloads/downloads"
RAIS_SOURCE="Ministério do Trabalho e Emprego - RAIS 2025"
RAIS_URL="https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais/rais-2025/rais-2025"

# First audited wave. Keep title because the exact Brazilian occupation label is
# part of the provenance and may be narrower than the EarnWage label.
CBO={
 "accountant":{"code":"252210","title":"Contador"},
 "financial_analyst":{"code":"252545","title":"Analista financeiro (instituições financeiras)"},
 "teacher":{"code":"231210","title":"Professor de nível superior do ensino fundamental (primeira a quarta série)"},
 "preschool_teacher":{"code":"231105","title":"Professor de nível superior na educação infantil (quatro a seis anos)"},
 "warehouse_operator":{"code":"414110","title":"Armazenista"},
 "sales_assistant":{"code":"354125","title":"Assistente de vendas"},
 "supermarket_worker":{"code":"421125","title":"Operador de caixa"},
 "bus_driver":{"code":"782410","title":"Motorista de ônibus urbano"},
 "industrial_operator":{"code":"862150","title":"Operador de máquinas fixas, em geral"},
 "construction_worker":{"code":"717020","title":"Servente de obras"},
 "cybersecurity_specialist":{"code":"212320","title":"Administrador em segurança da informação"},
 "agricultural_worker":{"code":"621005","title":"Trabalhador agropecuário em geral"},
 "auditor":{"code":"252205","title":"Auditor (contadores e afins)"},
 "doctor":{"code":"225125","title":"Médico clínico"},
 "nurse":{"code":"223505","title":"Enfermeiro"},
 "pharmacist":{"code":"223405","title":"Farmacêutico"},
 "psychologist":{"code":"251510","title":"Psicólogo clínico"},
 "physiotherapist":{"code":"223605","title":"Fisioterapeuta geral"},
 "software_developer":{"code":"212405","title":"Analista de desenvolvimento de sistemas"},
 "civil_engineer":{"code":"214205","title":"Engenheiro civil"},
 "mechanical_engineer":{"code":"214405","title":"Engenheiro mecânico"},
 "architect":{"code":"214105","title":"Arquiteto de edificações"},
 "administrative_assistant":{"code":"411010","title":"Assistente administrativo"},
 "receptionist":{"code":"422105","title":"Recepcionista, em geral"},
 "truck_driver":{"code":"782510","title":"Motorista de caminhão (rotas regionais e internacionais)"},
 "electrician":{"code":"715615","title":"Eletricista de instalações"},
 "plumber":{"code":"724110","title":"Encanador"},
 "cook":{"code":"513205","title":"Cozinheiro geral"},
 "waiter":{"code":"513405","title":"Garçom"},
 "cleaner":{"code":"514320","title":"Faxineiro"},
 "security_guard":{"code":"517330","title":"Vigilante"},
 "lawyer":{"code":"241005","title":"Advogado"},
 "dentist":{"code":"223208","title":"Cirurgião dentista - clínico geral"},
 "welder":{"code":"724315","title":"Soldador"},
 "automotive_mechanic":{"code":"914405","title":"Mecânico de manutenção de automóveis, motocicletas e veículos similares"},
}

def mapping(occupation):
 row=CBO.get(occupation)
 if not row:
  return {"status":"unavailable","country":"BR","occupation":occupation,
          "classification":"CBO2002","reason":"No audited direct CBO occupation mapping yet"}
 return {"status":"available","country":"BR","occupation":occupation,
         "classification":"CBO2002","code":row["code"],"source_label":row["title"],
         "source":SOURCE,"source_url":SOURCE_URL,
         "note":"Classification mapping only; this object is not a salary observation."}

def coverage():
 return {occupation: row["code"] for occupation,row in CBO.items()}
