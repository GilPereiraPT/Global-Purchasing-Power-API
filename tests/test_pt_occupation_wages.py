"""Offline synthetic schema tests; sample amounts are NOT official observations."""
import json

import pytest
import httpx
from fastapi.testclient import TestClient

from app import pt_occupation_wages as pt
from app import store
from app.main import app


def fixture():
    return [{"IndicadorCod":"0010385",
             "IndicadorDsg":"Ganho médio mensal (€) por Localização geográfica e Profissão (CPP)",
             "Dados":{"2024":[
                 {"geocod":"1","geodsg":"Portugal","dim_3":"2",
                  "dim_3_t":"Especialistas","valor":"2499,99"},
                 {"geocod":"1","geodsg":"Portugal","dim_3":"2211",
                  "dim_3_t":"Médicos de clínica geral","valor":"3500,50"},
                 {"geocod":"1","geodsg":"Portugal","dim_3":"2221",
                  "dim_3_t":"Enfermeiros","valor":"1850,25"},
                 {"geocod":"1","geodsg":"Portugal","dim_3":"2634",
                  "dim_3_t":"Psicólogos","valor":"2100,10"},
                 {"geocod":"2","geodsg":"Norte","dim_3":"2221",
                  "dim_3_t":"Enfermeiros","valor":"1000,00"}]} }]


def mapping():
    return {"indicator":"0010385","occupation_dimension":"dim_3",
            "geography":{"code":"1","label":"Portugal"},
            "occupations":[
                {"occupation":"doctor","cpp_code":"2211",
                 "cpp_label":"Médicos de clínica geral"},
                {"occupation":"nurse","cpp_code":"2221","cpp_label":"Enfermeiros"},
                {"occupation":"psychologist","cpp_code":"2634","cpp_label":"Psicólogos"}]}


def test_source_inspection_does_not_turn_major_group_into_salary():
    result=pt.inspect(fixture())
    assert result["indicator"]=="0010385"
    assert len(result["dimensions"]["dim_3"])==4
    assert any(item["code"]=="2" for item in result["dimensions"]["dim_3"])
    rows=pt.build_records(fixture(),mapping())
    assert len(rows)==3
    assert [r["occupation"] for r in rows]==["doctor","nurse","psychologist"]
    assert {r["occupation"]:r["value"] for r in rows}=={
        "doctor":3500.5,"nurse":1850.25,"psychologist":2100.1}
    assert all(r["classification"].startswith("CPP2010:") for r in rows)
    assert all(r["unit"]=="EUR/month" for r in rows)


def test_source_wrong_id_geography_group_and_label_fail_closed():
    source=fixture()
    source[0]["IndicadorCod"]="0000000"
    with pytest.raises(ValueError,match="Incorrect"):
        pt.build_records(source,mapping())
    bad=mapping()
    bad["occupations"][0]["cpp_code"]="22"
    with pytest.raises(ValueError,match="4-digit"):
        pt.build_records(fixture(),bad)
    bad=mapping()
    bad["geography"]["label"]="Continente"
    with pytest.raises(ValueError,match="Portugal"):
        pt.build_records(fixture(),bad)
    bad=mapping()
    bad["occupations"][1]["cpp_label"]="Profissionais de saúde"
    with pytest.raises(ValueError,match="label drift"):
        pt.build_records(fixture(),bad)


def test_invalid_ine_amount_and_duplicate_do_not_create_fake_wage():
    raw=fixture()
    raw[0]["Dados"]["2024"][2]["valor"]="x"
    selected=pt.build_records(raw,mapping())
    assert len(selected)==2
    assert "nurse" not in {r["occupation"] for r in selected}
    raw=fixture()
    raw[0]["Dados"]["2024"].append(dict(raw[0]["Dados"]["2024"][2]))
    with pytest.raises(ValueError,match="Duplicate"):
        pt.build_records(raw,mapping())


def test_verified_snapshot_import_and_occupation_cards(monkeypatch,tmp_path):
    monkeypatch.setattr(store,"DB_PATH",str(tmp_path/"existing.sqlite3"))
    snapshot=tmp_path/"pt.json"
    result=pt.export(fixture(),mapping(),snapshot)
    assert result["exported"]==3
    assert pt.load_snapshot(snapshot)==3
    assert pt.load_snapshot(snapshot)==3  # idempotent
    assert len(pt.observed_coverage())==3
    with TestClient(app) as client:
        amounts={}
        for occupation in ("doctor","nurse","psychologist"):
            r=client.get("/v1/earnwage/overview",
                         params={"country":"PT","occupation":occupation})
            assert r.status_code==200
            data=r.json()
            assert data["national_occupation_wage"]["status"]=="available"
            assert data["annual_presentation"]["status"]=="available"
            assert data["annual_presentation"]["kind"]=="annualized_12_month_equivalent"
            assert data["annual_presentation"]["payments_verified"] is False
            assert data["national_major_group_context"]["precision"]=="isco08_major_group"
            amounts[occupation]=data["annual_presentation"]["value"]
        assert len(set(amounts.values()))==3
        inventory=client.get("/v1/data-inventory").json()
        country=next(c for c in inventory["countries"] if c["code"]=="PT")
        assert country["exact_occupational_wages"]["available_occupations"]==3
        assert inventory["summary"]["exact_occupational_wages"]["by_source_observations"]["INE_GEP"]==3


def test_snapshot_tampering_rejected_before_database_write(monkeypatch,tmp_path):
    monkeypatch.setattr(store,"DB_PATH",str(tmp_path/"protected.sqlite3"))
    p=tmp_path/"pt.json"
    pt.export(fixture(),mapping(),p)
    obj=json.loads(p.read_text(encoding="utf-8"))
    obj["records"][1]["classification"]="CPP2010:22"
    p.write_text(json.dumps(obj),encoding="utf-8")
    with pytest.raises(ValueError,match="Invalid Portuguese wage"):
        pt.load_snapshot(p)
    assert pt.observed_coverage()=={}


def test_ine_transient_timeout_then_recovery(monkeypatch):
    attempts=[]
    pauses=[]

    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def raise_for_status(self): return None
        def iter_bytes(self): yield json.dumps(fixture()).encode("utf-8")

    class Client:
        def __init__(self,**kwargs):
            attempts.append(kwargs)
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def stream(self,method,url):
            assert method=="GET" and url==pt.URL
            if len(attempts)==1:
                raise httpx.ConnectTimeout("network timed out")
            return Response()

    monkeypatch.setattr(pt.httpx,"Client",Client)
    monkeypatch.setattr(pt.time,"sleep",pauses.append)
    assert pt.fetch()==fixture()
    assert len(attempts)==2
    assert pauses==[3]
    timeout=attempts[0]["timeout"]
    assert timeout.connect==18.0 and timeout.read==75.0


def test_ine_3_timeouts_fail_with_safe_diagnostic(monkeypatch):
    count=[]
    class Client:
        def __init__(self,**kwargs): count.append(True)
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def stream(self,method,url):
            raise httpx.ConnectTimeout("secret proxy endpoint must not be printed")
    monkeypatch.setattr(pt.httpx,"Client",Client)
    monkeypatch.setattr(pt.time,"sleep",lambda seconds:None)
    with pytest.raises(RuntimeError,match="No data were imported"):
        pt.fetch()
    assert len(count)==3


def test_ine_malformed_success_payload_never_retried(monkeypatch):
    count=[]
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def raise_for_status(self): return None
        def iter_bytes(self): yield b"<html>Blocked</html>"
    class Client:
        def __init__(self,**kwargs): count.append(True)
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def stream(self,method,url): return Response()
    monkeypatch.setattr(pt.httpx,"Client",Client)
    with pytest.raises(json.JSONDecodeError):
        pt.fetch()
    assert len(count)==1


def test_offline_inspection_never_opens_a_network_socket(monkeypatch,tmp_path,capsys):
    raw=tmp_path/"ine.json"
    raw.write_text(json.dumps(fixture()),encoding="utf-8")
    monkeypatch.setattr(pt,"fetch",lambda:pytest.fail("No network allowed in --source"))
    assert pt.main(["--source",str(raw),"--inspect"])==0
    assert '"indicator": "0010385"' in capsys.readouterr().out
