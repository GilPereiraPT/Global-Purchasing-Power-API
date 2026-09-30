"""Ireland CSO SES 2022 occupational-group earnings context.

These are broad occupational-group statistics, never exact profession salaries.
Agriculture, forestry and fishing are outside the SES 2022 coverage.
"""
SOURCE = "CSO Ireland, Structure of Earnings Survey 2022"
SOURCE_URL = "https://www.cso.ie/en/releasesandpublications/ep/p-ses/structureofearningssurvey2022/occupationandeducation/"
PERIOD = "2022"

GROUPS = {
 "1": {"label":"Managers, Directors & Senior Officials","mean_hourly":42.67,"median_hourly":30.53},
 "2": {"label":"Professional","mean_hourly":38.41,"median_hourly":32.99},
 "3": {"label":"Associate Professional & Technical","mean_hourly":28.70,"median_hourly":23.87},
 "4": {"label":"Administrative & Secretarial","mean_hourly":21.04,"median_hourly":17.84},
 "5": {"label":"Caring, Leisure & Other Services / Sales & Customer Service","mean_hourly":None,"median_hourly":None},
 "7": {"label":"Skilled Trades","mean_hourly":20.74,"median_hourly":17.10},
 "8": {"label":"Process, Plant & Machine Operatives","mean_hourly":20.24,"median_hourly":17.27},
 "9": {"label":"Elementary","mean_hourly":16.50,"median_hourly":13.43},
}
# ISCO major group 5 spans two SES categories, so map professions explicitly.
GROUP5 = {
 "sales_assistant":{"label":"Sales & Customer Service","mean_hourly":16.22,"median_hourly":14.05},
 "supermarket_worker":{"label":"Sales & Customer Service","mean_hourly":16.22,"median_hourly":14.05},
 "cook":{"label":"Skilled Trades","mean_hourly":20.74,"median_hourly":17.10},
 "waiter":{"label":"Caring, Leisure & Other Services","mean_hourly":18.73,"median_hourly":15.74},
 "security_guard":{"label":"Caring, Leisure & Other Services","mean_hourly":18.73,"median_hourly":15.74},
 "healthcare_assistant":{"label":"Caring, Leisure & Other Services","mean_hourly":18.73,"median_hourly":15.74},
}

def context(occupation, major_group):
 if occupation == "agricultural_worker":
  return {"status":"unavailable","country":"IE","occupation":occupation,
          "precision":"occupational_group","reason":"SES 2022 excludes agriculture, forestry and fishing"}
 row = GROUP5.get(occupation) if major_group == "5" else GROUPS.get(major_group)
 if not row or row.get("median_hourly") is None:
  return {"status":"unavailable","country":"IE","occupation":occupation,
          "precision":"occupational_group","reason":"No validated CSO SES occupational-group mapping"}
 return {"status":"available","country":"IE","occupation":occupation,"period":PERIOD,
         "precision":"occupational_group","source_label":row["label"],
         "values":{"mean":{"value":row["mean_hourly"],"currency":"EUR","unit":"gross/hour"},
                   "median":{"value":row["median_hourly"],"currency":"EUR","unit":"gross/hour"}},
         "source":SOURCE,"source_url":SOURCE_URL,
         "note":"Official CSO occupational-group context. It is not the salary of the selected profession and is not annualized."}
