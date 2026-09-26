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
    ("US", "United States", "Washington, D.C.", "USD", None),
    ("CA", "Canada", "Ottawa", "CAD", None),
]
# One Portuguese locale shared by Portugal and Brazil; no pt-PT/pt-BR split.
SUPPORTED_LANGUAGES = {
    "en": "English", "pt": "Português", "es": "Español",
    "de": "Deutsch", "fr": "Français", "it": "Italiano",
    "nl": "Nederlands",
}
COUNTRY_INTERFACE_LANGUAGES = {
    "PT": ["pt"], "BR": ["pt"], "GB": ["en"], "IN": ["en"],
    "PK": ["en"], "US": ["en"], "CA": ["en", "fr"],
    "ES": ["es"], "DE": ["de"], "FR": ["fr"],
    "NL": ["nl"], "IT": ["it"], "CH": ["de", "fr", "it"],
    "IE": ["en"],
}
COUNTRY_MAP = {
    code: {"code": code, "name": name, "capital": capital, "currency": currency,
           "interface_languages": COUNTRY_INTERFACE_LANGUAGES[code],
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

# Curated interface labels. The API IDs and ISCO mappings never depend on language.
JOB_TRANSLATIONS = {
    "accountant": {"es": "Contable", "de": "Buchhalter/in", "fr": "Comptable", "it": "Contabile", "nl": "Accountant"},
    "auditor": {"es": "Auditor/a", "de": "Wirtschaftsprüfer/in", "fr": "Auditeur / auditrice", "it": "Revisore contabile", "nl": "Auditor"},
    "financial_analyst": {"es": "Analista financiero", "de": "Finanzanalyst/in", "fr": "Analyste financier / financière", "it": "Analista finanziario", "nl": "Financieel analist"},
    "doctor": {"es": "Médico/a", "de": "Arzt / Ärztin", "fr": "Médecin", "it": "Medico", "nl": "Arts"},
    "nurse": {"es": "Enfermero/a", "de": "Pflegefachkraft", "fr": "Infirmier / infirmière", "it": "Infermiere / infermiera", "nl": "Verpleegkundige"},
    "pharmacist": {"es": "Farmacéutico/a", "de": "Apotheker/in", "fr": "Pharmacien / pharmacienne", "it": "Farmacista", "nl": "Apotheker"},
    "psychologist": {"es": "Psicólogo/a", "de": "Psychologe / Psychologin", "fr": "Psychologue", "it": "Psicologo / psicologa", "nl": "Psycholoog"},
    "physiotherapist": {"es": "Fisioterapeuta", "de": "Physiotherapeut/in", "fr": "Kinésithérapeute", "it": "Fisioterapista", "nl": "Fysiotherapeut"},
    "teacher": {"es": "Profesor/a", "de": "Lehrer/in", "fr": "Enseignant / enseignante", "it": "Insegnante", "nl": "Docent"},
    "preschool_teacher": {"es": "Educador/a infantil", "de": "Erzieher/in", "fr": "Éducateur / éducatrice de jeunes enfants", "it": "Educatore / educatrice dell’infanzia", "nl": "Pedagogisch medewerker"},
    "software_developer": {"es": "Desarrollador/a de software", "de": "Softwareentwickler/in", "fr": "Développeur / développeuse logiciel", "it": "Sviluppatore / sviluppatrice software", "nl": "Softwareontwikkelaar"},
    "it_technician": {"es": "Técnico/a informático/a", "de": "IT-Techniker/in", "fr": "Technicien / technicienne informatique", "it": "Tecnico / tecnica informatico/a", "nl": "IT-technicus"},
    "civil_engineer": {"es": "Ingeniero/a civil", "de": "Bauingenieur/in", "fr": "Ingénieur / ingénieure civil(e)", "it": "Ingegnere civile", "nl": "Civiel ingenieur"},
    "mechanical_engineer": {"es": "Ingeniero/a mecánico/a", "de": "Maschinenbauingenieur/in", "fr": "Ingénieur / ingénieure mécanique", "it": "Ingegnere meccanico", "nl": "Werktuigbouwkundig ingenieur"},
    "architect": {"es": "Arquitecto/a", "de": "Architekt/in", "fr": "Architecte", "it": "Architetto / architetta", "nl": "Architect"},
    "administrative_assistant": {"es": "Asistente administrativo/a", "de": "Verwaltungsassistent/in", "fr": "Assistant / assistante administratif/ve", "it": "Assistente amministrativo/a", "nl": "Administratief medewerker"},
    "manager": {"es": "Gestor/a", "de": "Manager/in", "fr": "Responsable de gestion", "it": "Responsabile", "nl": "Manager"},
    "receptionist": {"es": "Recepcionista", "de": "Empfangsmitarbeiter/in", "fr": "Réceptionniste", "it": "Addetto/a alla reception", "nl": "Receptionist"},
    "sales_assistant": {"es": "Dependiente/a", "de": "Verkäufer/in", "fr": "Vendeur / vendeuse", "it": "Addetto/a alle vendite", "nl": "Verkoopmedewerker"},
    "supermarket_worker": {"es": "Empleado/a de supermercado", "de": "Supermarktmitarbeiter/in", "fr": "Employé / employée de supermarché", "it": "Addetto/a al supermercato", "nl": "Supermarktmedewerker"},
    "truck_driver": {"es": "Conductor/a de camión", "de": "Lkw-Fahrer/in", "fr": "Conducteur / conductrice de poids lourd", "it": "Autista di camion", "nl": "Vrachtwagenchauffeur"},
    "bus_driver": {"es": "Conductor/a de autobús", "de": "Busfahrer/in", "fr": "Conducteur / conductrice de bus", "it": "Autista di autobus", "nl": "Buschauffeur"},
    "electrician": {"es": "Electricista", "de": "Elektriker/in", "fr": "Électricien / électricienne", "it": "Elettricista", "nl": "Elektricien"},
    "plumber": {"es": "Fontanero/a", "de": "Installateur/in für Sanitärtechnik", "fr": "Plombier / plombière", "it": "Idraulico/a", "nl": "Loodgieter"},
    "construction_worker": {"es": "Trabajador/a de la construcción", "de": "Bauarbeiter/in", "fr": "Ouvrier / ouvrière du bâtiment", "it": "Operaio/a edile", "nl": "Bouwvakker"},
    "cook": {"es": "Cocinero/a", "de": "Koch / Köchin", "fr": "Cuisinier / cuisinière", "it": "Cuoco / cuoca", "nl": "Kok"},
    "waiter": {"es": "Camarero/a", "de": "Kellner/in", "fr": "Serveur / serveuse", "it": "Cameriere / cameriera", "nl": "Ober"},
    "cleaner": {"es": "Personal de limpieza", "de": "Reinigungskraft", "fr": "Agent / agente de nettoyage", "it": "Addetto/a alle pulizie", "nl": "Schoonmaker"},
    "security_guard": {"es": "Vigilante de seguridad", "de": "Sicherheitsmitarbeiter/in", "fr": "Agent / agente de sécurité", "it": "Addetto/a alla sicurezza", "nl": "Beveiliger"},
    "lawyer": {"es": "Abogado/a", "de": "Rechtsanwalt / Rechtsanwältin", "fr": "Avocat / avocate", "it": "Avvocato / avvocata", "nl": "Advocaat"},
    "dentist": {"es": "Dentista", "de": "Zahnarzt / Zahnärztin", "fr": "Dentiste", "it": "Dentista", "nl": "Tandarts"},
    "healthcare_assistant": {"es": "Auxiliar sanitario/a", "de": "Pflegehelfer/in", "fr": "Aide-soignant / aide-soignante", "it": "Operatore / operatrice sociosanitario/a", "nl": "Zorgassistent"},
    "data_analyst": {"es": "Analista de datos", "de": "Datenanalyst/in", "fr": "Analyste de données", "it": "Analista dei dati", "nl": "Data-analist"},
    "cybersecurity_specialist": {"es": "Especialista en ciberseguridad", "de": "Cybersicherheitsspezialist/in", "fr": "Spécialiste en cybersécurité", "it": "Specialista in cybersicurezza", "nl": "Cybersecurityspecialist"},
    "secondary_teacher": {"es": "Profesor/a de secundaria", "de": "Sekundarschullehrer/in", "fr": "Enseignant / enseignante du secondaire", "it": "Insegnante di scuola secondaria", "nl": "Docent voortgezet onderwijs"},
    "warehouse_operator": {"es": "Operario/a de almacén", "de": "Lagermitarbeiter/in", "fr": "Magasinier / magasinière", "it": "Magazziniere/a", "nl": "Magazijnmedewerker"},
    "industrial_operator": {"es": "Operario/a industrial", "de": "Industrieanlagenbediener/in", "fr": "Opérateur / opératrice industriel/le", "it": "Operatore / operatrice industriale", "nl": "Industrieel operator"},
    "welder": {"es": "Soldador/a", "de": "Schweißer/in", "fr": "Soudeur / soudeuse", "it": "Saldatore / saldatrice", "nl": "Lasser"},
    "automotive_mechanic": {"es": "Mecánico/a de automóviles", "de": "Kfz-Mechaniker/in", "fr": "Mécanicien / mécanicienne automobile", "it": "Meccanico/a d’auto", "nl": "Automonteur"},
    "agricultural_worker": {"es": "Trabajador/a agrícola", "de": "Landarbeiter/in", "fr": "Ouvrier / ouvrière agricole", "it": "Lavoratore / lavoratrice agricolo/a", "nl": "Landarbeider"},
}
JOB_ALIASES = {
    "accountant": {"pt": ["contabilidade", "técnico de contabilidade"], "en": ["accounting", "accounts"], "es": ["contabilidad"], "de": ["Buchhaltung"], "fr": ["comptabilité"], "it": ["contabilità"], "nl": ["boekhouding"]},
    "software_developer": {"pt": ["programador", "desenvolvedor de software"], "en": ["programmer", "software engineer"]},
    "doctor": {"pt": ["médica"], "en": ["physician"]},
}

from app.occupations import EXTRA_JOBS, ISCO08_EXACT

JOBS.extend(EXTRA_JOBS)
OCCUPATIONS = [
    {"id": key, "isco08": ISCO08_EXACT.get(key),
     "translations": {"pt": pt, "en": en, **JOB_TRANSLATIONS[key]},
     "aliases": JOB_ALIASES.get(key, {})} for key, pt, en in JOBS
]
assert len(OCCUPATIONS) == 40

