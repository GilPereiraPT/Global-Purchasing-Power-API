import sqlite3
from app import data_inventory as inventory
from app.us_oews import init


def test_bls_inventory_is_read_only_and_national(tmp_path):
    db=sqlite3.connect(tmp_path/'isolated.sqlite3');init(db)
    db.execute("INSERT INTO us_oews(reference_period,published_year,source_file,area,area_type,prim_state,naics,i_group,own_code,occ_code,o_group,occ_title,source_url,a_mean) VALUES('May 2021',2021,'source.xlsx','99','1','','000000','','1235','15-1252','detailed','Software Developers','https://www.bls.gov/oes/tables.htm',120000)")
    db.execute("INSERT INTO us_oews(reference_period,published_year,source_file,area,area_type,prim_state,naics,i_group,own_code,occ_code,o_group,occ_title,source_url,a_mean) VALUES('May 2025',2025,'source.xlsx','01','2','AL','000000','','1235','15-1252','detailed','Software Developers','https://www.bls.gov/oes/tables.htm',130000)")
    db.commit();db.execute('PRAGMA query_only=ON')
    tables=db.execute('SELECT name FROM sqlite_master').fetchall()
    result=inventory._wages(db)
    assert result['BLS_OEWS'][('US','software_developer')]==(1,'May 2021')
    assert db.execute('SELECT name FROM sqlite_master').fetchall()==tables


def test_missing_wage_tables_are_not_created(tmp_path):
    db=sqlite3.connect(tmp_path/'empty.sqlite3');db.execute('PRAGMA query_only=ON')
    assert all(not rows for rows in inventory._wages(db).values())
    assert db.execute('SELECT name FROM sqlite_master').fetchall()==[]


def test_source_union_and_alias_rows_counted_once(tmp_path,monkeypatch):
    from app import store
    from tests.test_data_manager import setup
    setup(monkeypatch,tmp_path)
    with store.connect() as db:
        init(db)
        for code,title in [('13-2011','Accountants and Auditors'),('15-1252','Software Developers')]:
            db.execute("INSERT INTO us_oews(reference_period,published_year,source_file,area,area_type,prim_state,naics,i_group,own_code,occ_code,o_group,occ_title,source_url,a_mean) VALUES('May 2025',2025,'source.xlsx','99','1','','000000','','1235',?,'detailed',?,'https://www.bls.gov/oes/tables.htm',100000)",(code,title))
        from app.north_america import init as na_init
        na_init(db)
        db.execute("INSERT INTO north_america_wages VALUES('US','software_developer','national','SOC2018:15-1252','Software Developers','May 2025',2025,'USD','mean','USD/year',100000,'BLS','https://www.bls.gov/oes/tables.htm')")
        db.commit()
    result=inventory.build_inventory();us=next(c for c in result['countries'] if c['code']=='US')
    jobs=us['exact_occupational_wages']['occupations']
    assert sum(j['status']=='available' for j in jobs.values())==3
    assert len(jobs['software_developer']['sources'])==2
    assert result['summary']['exact_occupational_wages']['by_source_observations']['BLS_OEWS']==2
    assert result['summary']['bls_oews']['mapped_occupations']==3
