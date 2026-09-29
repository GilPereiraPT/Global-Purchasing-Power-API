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
