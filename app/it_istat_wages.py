"""Official Italian occupation-group earnings context from ISTAT SES 2022.

These are CP2021/ISCO-08 broad-group hourly earnings, not exact occupation wages.
"""
SOURCE="ISTAT, Rilevazione sulla struttura delle retribuzioni e del costo del lavoro 2022"
SOURCE_URL="https://www.istat.it/wp-content/uploads/2025/01/REPORT_STRUTTURA_RETRIBUZIONI_2022.pdf"
PERIOD="2022"
GROUPS={
 "1":{"label":"Dirigenti","female":34.5,"male":49.8},
 "2":{"label":"Professioni intellettuali e scientifiche","female":23.4,"male":25.5},
 "3":{"label":"Professioni tecniche intermedie","female":16.0,"male":19.0},
 "4":{"label":"Impiegati di ufficio","female":13.5,"male":15.0},
 "5":{"label":"Professioni nelle attività commerciali e nei servizi","female":10.8,"male":13.0},
 "6":{"label":"Personale specializzato addetto all'agricoltura, foreste e pesca","female":10.0,"male":12.0},
 "7":{"label":"Artigiani e operai specializzati","female":10.6,"male":12.8},
 "8":{"label":"Conduttori di impianti e macchinari e addetti al montaggio","female":10.8,"male":13.0},
 "9":{"label":"Professioni non qualificate","female":10.0,"male":11.0},
}
def context(occupation, major_group, caution=None):
    row=GROUPS.get(str(major_group))
    if not row:
        return {"status":"unavailable","country":"IT","occupation":occupation,
                "precision":"cp2021_major_group","reason":"No validated ISTAT group mapping"}
    return {"status":"available","country":"IT","occupation":occupation,"period":PERIOD,
            "cp2021_major_group":str(major_group),"group_label":row["label"],
            "precision":"cp2021_major_group","geography":"Italy","currency":"EUR",
            "unit":"gross_hourly_mean","values":{"female":row["female"],"male":row["male"]},
            "source":SOURCE,"source_url":SOURCE_URL,"mapping_caution":caution,
            "note":"Official ISTAT CP2021 broad-group context, not an individual occupation wage. Values are average gross hourly earnings by sex for October 2022."}


# Profession-specific initial RAL from Excelsior 2025, based on INPS
# Sistema Informativo Professioni data for 2023. Only explicit matches are used.
EXCELSIOR_SOURCE="Unioncamere-ANPAL Sistema Informativo Excelsior, Laureati e lavoro 2025"
EXCELSIOR_SOURCE_URL="https://excelsior.unioncamere.net/sites/default/files/pubblicazioni/2025/Lavoro_dopo_studi.pdf"
INITIAL_RAL={
    "lawyer":{"value":46800,"cp2021":"2.5.2.1.0","label":"Avvocati"},
    "psychologist":{"value":36400,"cp2021":"2.5.3.3.1","label":"Psicologi clinici e psicoterapeuti"},
    "data_analyst":{"value":34300,"cp2021":"2.1.1.3.2","label":"Statistici e analisti di dati"},
    "preschool_teacher":{"value":24800,"cp2021":None,"label":"Docenti di scuola pre-primaria"},
    "secondary_teacher":{"value":30300,"cp2021":None,"label":"Docenti di scienze letterarie, artistiche, storiche, filosofiche, pedagogiche e psicologiche nella scuola secondaria superiore"},
    "security_guard":{"value":20800,"cp2021":None,"label":"Guardie private di sicurezza"},
    "administrative_assistant":{"value":24500,"cp2021":None,"label":"Addetti a funzioni di segreteria"},
    "welder":{"value":26600,"cp2021":"6.2.1.2.0","label":"Saldatori e tagliatori a fiamma"},
}
def occupation_wage(occupation):
    row=INITIAL_RAL.get(occupation)
    if not row:
        return {"status":"unavailable","country":"IT","occupation":occupation,
                "precision":"exact_profession_initial_salary",
                "reason":"No explicit profession-level initial RAL verified in the current Excelsior/INPS table"}
    return {"status":"available","country":"IT","occupation":occupation,"period":"2023",
            "value":row["value"],"currency":"EUR","unit":"gross/year",
            "measure":"initial_gross_annual_salary","precision":"profession_specific",
            "cp2021":row["cp2021"],"source_label":row["label"],
            "source":EXCELSIOR_SOURCE,"source_url":EXCELSIOR_SOURCE_URL,
            "note":"Initial gross annual remuneration (RAL), not national mean salary. INPS data supplied within Sistema Informativo Professioni and published in Excelsior 2025."}


def observed_coverage():
    """Profession-level coverage only; broad CP2021 context is deliberately excluded."""
    return {occupation: "2023" for occupation in INITIAL_RAL}
