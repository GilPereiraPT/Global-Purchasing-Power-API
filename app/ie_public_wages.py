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
}
def wage(occupation):
 row=ENTRY.get(occupation)
 if not row:
  return {"status":"unavailable","country":"IE","occupation":occupation,"precision":"public_sector_entry","reason":"No direct Irish public-sector entry scale mapped for this occupation"}
 return {"status":"available","country":"IE","occupation":occupation,"period":PERIOD,"value":row["value"],"currency":"EUR","unit":"gross/year","measure":"public_sector_entry_salary","precision":"public_sector_entry","source_label":row["label"],"grade_code":row["grade_code"],"source":SOURCE,"source_url":SOURCE_URL,"note":"Official HSE public-sector entry point. This is not a national occupation mean or median."}
def observed_coverage():
 return {occupation: PERIOD for occupation in ENTRY}
