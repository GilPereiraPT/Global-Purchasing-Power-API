"""Irish public-sector entry salary benchmarks; not national occupation averages."""
SOURCE="HSE, Consolidated Salary Scales, 1 February 2026"
SOURCE_URL="https://assets.hse.ie/media/documents/February_2026_pay_scales.pdf"
PERIOD="2026-02-01"
ENTRY={
 "nurse":{"value":37788,"label":"Staff Nurse","grade_code":"2135"},
 "pharmacist":{"value":49985,"label":"Pharmacist","grade_code":"3247"},
 "physiotherapist":{"value":45063,"label":"Physiotherapist","grade_code":"314X"},
 "psychologist":{"value":62596,"label":"Psychologist, Clinical","grade_code":"3689"},
 "healthcare_assistant":{"value":36288,"label":"Health Care Assistant","grade_code":"6075"},
 "teacher":{"value":45379,"label":"Primary Teacher - new entrant","grade_code":"DEY-0004-2026"},
 "secondary_teacher":{"value":46948,"label":"Post-Primary Teacher - new entrant","grade_code":"DEY-0005-2026"},
 "dentist":{"value":74821,"label":"General Dental Surgeon","grade_code":"1597"},
}
EDUCATION_SOURCE="Department of Education and Youth, Circulars 0004/2026 and 0005/2026"
EDUCATION_URL="https://www.gov.ie/en/department-of-education/circulars/"

def wage(occupation):
 row=ENTRY.get(occupation)
 if not row:
  return {"status":"unavailable","country":"IE","occupation":occupation,"precision":"public_sector_entry","reason":"No direct Irish public-sector entry scale mapped for this occupation"}
 source = EDUCATION_SOURCE if occupation in ("teacher","secondary_teacher") else SOURCE
 source_url = EDUCATION_URL if occupation in ("teacher","secondary_teacher") else SOURCE_URL
 return {"status":"available","country":"IE","occupation":occupation,"period":PERIOD,"value":row["value"],"currency":"EUR","unit":"gross/year","measure":"public_sector_entry_salary","precision":"public_sector_entry","source_label":row["label"],"grade_code":row["grade_code"],"source":source,"source_url":source_url,"note":"Official Irish public-sector entry point. This is not a national occupation mean or median."}
def observed_coverage():
 return {occupation: PERIOD for occupation in ENTRY}
