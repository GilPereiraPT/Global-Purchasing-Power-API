"""Irish public-sector entry salary benchmarks; not national occupation averages."""
HSE_SOURCE="HSE, Consolidated Salary Scales, 1 June 2026"
HSE_URL="https://healthservice.hse.ie/documents/10686/1_June_2026_pay_scales.pdf"
EDUCATION_SOURCE="Department of Education and Youth, Circulars 0004/2026 and 0005/2026"
EDUCATION_URL="https://www.gov.ie/en/department-of-education/circulars/"
PUBLICJOBS_SOURCE="PublicJobs.ie / Office of the Comptroller and Auditor General"
PUBLICJOBS_AUDITOR_URL="https://www.publicjobs.ie/en/information-hub/latest-news-and-events/1125-now-open-trainee-auditor"
PUBLICJOBS_ICT_URL="https://www.publicjobs.ie/en/information-hub/latest-news-and-events/1076-now-live-infrastructure-and-operations-ict-specialist-eo-in-the-civil-service"
PUBLICJOBS_CYBER_URL="https://publicjobs.ie/en/information-hub/latest-news-and-events/1061-new-opportunities-networks-and-cyber-security-senior-ict-specialist-heo-in-the-civil-service"

ENTRY={
 "nurse":{"value":38166,"label":"Staff Nurse","grade_code":"2135","period":"2026-06-01"},
 "pharmacist":{"value":50485,"label":"Pharmacist","grade_code":"3247","period":"2026-06-01"},
 "physiotherapist":{"value":45514,"label":"Physiotherapist","grade_code":"314X","period":"2026-06-01"},
 "psychologist":{"value":63222,"label":"Psychologist, Clinical","grade_code":"3689","period":"2026-06-01"},
 "healthcare_assistant":{"value":36651,"label":"Health Care Assistant","grade_code":"6075","period":"2026-06-01"},
 "dentist":{"value":75569,"label":"General Dental Surgeon","grade_code":"1597","period":"2026-06-01"},
 "doctor":{"value":47127,"label":"Intern","grade_code":"1554","period":"2026-06-01",
           "note":"Intern is used as the first HSE medical career entry point; it is not an experienced-doctor salary."},
 "electrician":{"value":42486,"label":"Electrician","grade_code":"5096","period":"2026-06-01"},
 "plumber":{"value":42486,"label":"Plumber","grade_code":"5134","period":"2026-06-01"},
 "cook":{"value":42486,"label":"Chef II with qualification","grade_code":"4529","period":"2026-06-01",
         "note":"Closest qualified HSE cooking grade; the separate Cook, Trainee grade is not used."},
 "security_guard":{"value":36651,"label":"Security Guard","grade_code":"4106","period":"2026-06-01"},
 "cleaner":{"value":35433,"label":"Cleaner","grade_code":"4113","period":"2026-06-01"},
 "administrative_assistant":{"value":31934,"label":"Clerical Officer Grade","grade_code":"0609","period":"2026-06-01",
                             "note":"Clerical Officer is used as the direct public-service clerical/administrative entry benchmark."},
 "lawyer":{"value":34650,"label":"Trainee Solicitor - Year 1","grade_code":"CSSO-TRAINEE-SOLICITOR","period":"2026",
           "source":"Chief State Solicitor’s Office","source_url":"https://www.gov.ie/en/chief-state-solicitors-office/organisation-information/careers-trainee-solicitor/",
           "note":"Year 1 salary in the State Trainee Solicitor Programme; public-sector legal career entry benchmark, not an experienced solicitor salary."},
 "accountant":{"value":39083,"label":"Professional Accountant Grade III","grade_code":"PROF-ACCOUNTANT-GIII","period":"2025-03-01",
               "source":"PublicJobs.ie / Civil Service","source_url":"https://www.publicjobs.ie/restapi/documents/Final_Principal_Conditions_of_Service_Professional_Accountant_Grade_III.pdf",
               "note":"Published Civil Service entry scale; entry is explicitly at the minimum. The located grade-specific scale is effective March 2025."},
 "it_technician":{"value":38419,"label":"Infrastructure and Operations - ICT Specialist (Executive Officer)","grade_code":"EO-ICT-INFRA","period":"2026",
                  "source":"PublicJobs.ie / Civil Service","source_url":PUBLICJOBS_ICT_URL,
                  "note":"Public Civil Service ICT role explicitly covering end-user technical support and ICT infrastructure."},
 "cybersecurity_specialist":{"value":59435,"label":"Networks and Cyber Security - Senior ICT Specialist (HEO)","grade_code":"HEO-ICT-CYBER","period":"2026",
                             "source":"PublicJobs.ie / Civil Service","source_url":PUBLICJOBS_CYBER_URL,
                             "note":"Public Civil Service specialist role explicitly dedicated to networks and cyber security."},
 "auditor":{"value":42541,"label":"Trainee Auditor","grade_code":"C&AG-TRAINEE-AUDITOR-2026","period":"2026",
            "source":PUBLICJOBS_SOURCE,"source_url":PUBLICJOBS_AUDITOR_URL,
            "note":"Current 2026 public recruitment starting salary for Trainee Auditor."},
 "teacher":{"value":45833,"label":"Primary Teacher - new entrant","grade_code":"DEY-0055-2026","period":"2026-06-01",
            "source":EDUCATION_SOURCE,"source_url":EDUCATION_URL},
 "secondary_teacher":{"value":47417,"label":"Post-Primary Teacher - new entrant","grade_code":"DEY-0056-2026","period":"2026-06-01",
                      "source":EDUCATION_SOURCE,"source_url":EDUCATION_URL},
}

def wage(occupation):
 row=ENTRY.get(occupation)
 if not row:
  return {"status":"unavailable","country":"IE","occupation":occupation,"precision":"public_sector_entry",
          "reason":"No direct Irish public-sector entry scale mapped for this occupation"}
 source=row.get("source",HSE_SOURCE)
 source_url=row.get("source_url",HSE_URL)
 note=row.get("note","Official Irish public-sector entry point. This is not a national occupation mean or median.")
 return {"status":"available","country":"IE","occupation":occupation,"period":row["period"],"value":row["value"],
         "currency":"EUR","unit":"gross/year","measure":"public_sector_entry_salary",
         "precision":"public_sector_entry","source_label":row["label"],"grade_code":row["grade_code"],
         "source":source,"source_url":source_url,"note":note}

def public_sector_coverage():
 return {occupation: row["period"] for occupation,row in ENTRY.items()}

# Backward-compatible alias; entries are public-sector benchmarks, not observed national wages.
def observed_coverage():
 return public_sector_coverage()
