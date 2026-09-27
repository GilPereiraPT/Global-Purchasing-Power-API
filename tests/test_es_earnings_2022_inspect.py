"""Synthetic schemas only: tests do not invent or publish Spanish wage data."""
import csv
import io
import json
import zipfile

from openpyxl import Workbook

from scripts.inspect_es_earnings_2022 import inspect_csv_file,inspect_zip,main


def sample_csv():
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=["CNO1","GANAN","FACTOR"],delimiter=";")
    writer.writeheader()
    writer.writerows([
        {"CNO1":"2","GANAN":"10000","FACTOR":"1.1"},
        {"CNO1":"2","GANAN":"20000","FACTOR":"1.2"},
        {"CNO1":"3","GANAN":"30000","FACTOR":"1.3"},
    ])
    return out.getvalue().encode("utf-8")


def test_csv_only_identifies_broad_occupation_no_wage_values_exposed():
    report=inspect_csv_file(io.BytesIO(sample_csv()),"synthetic.csv")
    assert report["occupation_fields"][0]["field"]=="CNO1"
    assert report["occupation_fields"][0]["code_lengths"]==[1]
    assert report["occupation_fields"][0]["sample_has_four_digit_numeric_codes"] is False
    assert report["salary_field_candidates"]==["GANAN"]
    assert report["weight_field_candidates"]==["FACTOR"]
    assert report["sample_rows_read"]==3
    assert "10000" not in json.dumps(report)


def test_detailed_sample_is_only_a_lead_not_auto_approval():
    src=("CNO4;GANAN;FEXP\n"
         "2151;35000;1.5\n"
         "2121;24000;2.0\n").encode("utf-8")
    report=inspect_csv_file(io.BytesIO(src),"synthetic.csv")
    assert report["occupation_fields"][0]["sample_has_four_digit_numeric_codes"] is True
    assert report["weight_field_candidates"]==["FEXP"]
    assert "35000" not in json.dumps(report)


def test_archive_shows_data_dictionary_matches_but_no_individual_rows(tmp_path,capsys):
    source=tmp_path/"ees_2022_synthetic.zip"
    wb=Workbook()
    sheet=wb.active
    sheet.append(["Variable","Definition"])
    sheet.append(["CNO1","Gran grupo de ocupación"])
    sheet.append(["GANAN","Ganancia bruta anual"])
    sheet.append(["FACTOR","Factor de elevación"])
    book=io.BytesIO()
    wb.save(book)
    with zipfile.ZipFile(source,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("microdatos.csv",sample_csv())
        z.writestr("diccionario.xlsx",book.getvalue())
    result=inspect_zip(source)
    assert result["status"]=="inspection_only_no_import"
    assert len(result["csv"])==1
    assert len(result["dictionaries"])==1
    assert result["dictionaries"][0]["sheets"][0]["matching_dictionary_lines"]
    assert main(["--zip",str(source)])==0
    shown=json.loads(capsys.readouterr().out)
    assert shown["csv"][0]["occupation_fields"][0]["code_lengths"]==[1]


def test_rejects_empty_csv_without_exporting_data():
    try:
        inspect_csv_file(io.BytesIO(b""),"bad.csv")
    except ValueError as exc:
        assert "Empty" in str(exc)
    else:
        assert False,"Empty source must not be silently accepted"
