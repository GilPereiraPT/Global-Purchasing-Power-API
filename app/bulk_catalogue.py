"""Discovery registry, not a claim that candidates were downloaded/validated."""
from app.catalog import COUNTRY_MAP

SOURCES = (
    ('world_bank', tuple(COUNTRY_MAP), 'https://api.worldbank.org/v2/', 'JSON paginated', '1960 onwards; indicator-dependent', 'national', None, 'monthly', 'CC BY 4.0; confirm indicator exceptions', 'live_download_and_schema_validated_2026_10_03', 1),
    ('eurostat', ('PT','ES','DE','FR','GB','IE','NL','CH','IT'), 'https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/', 'TSV gzip / SDMX', 'dataset-dependent', 'national and NUTS where published', 'ISCO-08; dataset-dependent', 'monthly', 'Eurostat reuse policy; attribution', 'live_download_and_schema_validated_2026_10_03', 2),
    ('ilostat', tuple(COUNTRY_MAP), 'https://rplumber.ilo.org/metadata/toc/indicator/?lang=en', 'CSV catalogue / RDS bulk', 'country and source-dependent', 'mostly national', 'ISCO versions; exact 4-digit required for individual wages', 'quarterly', 'ILO terms; verify per dataset', 'existing_importer_extend_after_catalogue_validation', 3),
    ('bls', ('US',), 'https://www.bls.gov/oes/tables.htm', 'ZIP XLSX', 'validated 2021-2025; earlier SOC/layouts pending', 'national/state/territory/metropolitan/nonmetropolitan', 'SOC2018', 'quarterly', 'US government public data; automated downloads may return 403', 'live_bulk_validated_2026_10_03', 4),
    ('job_bank', ('CA',), 'https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116', 'CSV bulk', 'release-specific; observation periods can span years', 'national/province/economic region', 'NOC2021', 'quarterly', 'Open Government Licence Canada', 'live_bulk_validated_2026_10_03', 4),
    ('ine_gep', ('PT',), 'https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd=0010385&lang=PT', 'JSON / statistical tables', 'indicator-dependent; inspect official metadata', 'published geography only', 'CPP2010', 'quarterly', 'CC BY 4.0; validate indicator metadata', 'existing_parser_mapping_review_required', 4),
    ('oecd', tuple(COUNTRY_MAP), 'https://sdmx.oecd.org/public/rest/v1/data/', 'SDMX CSV/JSON', 'dataflow-dependent; nonmembers not guaranteed', 'mostly national', 'varies by dataflow', 'monthly', 'OECD terms; 2024 licence revisions; confirm dataflow licence', 'candidate_dataflow_and_dimensions_unverified', 5),
    ('statcan', ('CA',), 'https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041701', 'CSV ZIP / WDS', 'table-dependent', 'national/province', 'NOC broad categories in existing table', 'monthly', 'Statistics Canada Open Licence', 'groups_only_not_exact_wages', 5),
    ('rais', ('BR',), 'https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais', 'annual administrative microdata', 'annual; layout changes', 'UF/municipality', 'CBO2002', 'quarterly', 'Check microdata access/terms; existing snapshots are third-party aggregates', 'official_bulk_layout_and_access_unverified', 5),
    ('ibge', ('BR',), 'https://servicodados.ibge.gov.br/api/v3/agregados', 'JSON SIDRA', 'table-dependent', 'national/UF where published', 'survey occupational groups; not automatically CBO', 'monthly', 'IBGE attribution; inspect table metadata', 'candidate_classification_review', 5),
    ('ons', ('GB',), 'https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/occupation4digitsoc2010ashetable14', 'ZIP XLSX ASHE', 'annual; SOC2010/2020 breaks', 'national; regional tables differ', 'SOC2020', 'quarterly', 'Open Government Licence v3.0', 'existing_parser_and_snapshot', 4),
    ('ba', ('DE',), 'https://statistik.arbeitsagentur.de/', 'XLSX / Entgeltatlas publications', 'annual; KldB versions', 'national/Land', 'KldB Berufsgattung; reject broader fallback', 'quarterly', 'BA reuse terms; no verified public bulk endpoint for exact occupations', 'bulk_endpoint_unverified', 5),
    ('insee', ('FR',), 'https://api.insee.fr/melodi/file/DS_DERA_PRIVE_ANNUEL/DS_DERA_PRIVE_ANNUEL_2024_CSV_FR', 'CSV bulk', 'release-dependent', 'national/private sector in existing dataset', 'PCS-ESE', 'quarterly', 'Confirm official dataset licence; preserve net EQTP definition', 'existing_snapshot_bulk_extension_candidate', 4),
    ('cbs', ('NL',), 'https://datasets.cbs.nl/odata/v1/CBS/86355NED', 'OData JSON', 'table-dependent', 'national in existing table', 'BRC2014 edition2025', 'quarterly', 'CBS open data attribution', 'existing_snapshot_group_precision', 4),
    ('ine_es', ('ES',), 'https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/28186', 'JSON EAES', 'annual', 'national/regions by table', 'CNO11 major groups in existing table', 'quarterly', 'INE Spain reuse conditions', 'groups_only_not_exact_wages', 5),
    ('fso', ('CH',), 'https://www.pxweb-admin-a.bfs.admin.ch/pxweb/en/px-x-0304010000_205/-/px-x-0304010000_205.px/', 'PXWeb JSON/CSV', 'biennial ESS', 'national/regions by table', 'CH-ISCO19 1-2 digit groups', 'quarterly', 'FSO open data terms', 'audited_group_only', 5),
    ('istat', ('IT',), 'https://www.istat.it/comunicato-stampa/la-struttura-delle-retribuzioni-in-italia-anno-2022/', 'XLSX SES / SDMX candidate', 'SES periodic survey', 'published aggregate geography', 'CP2021 broad groups in published tables', 'quarterly', 'Istat attribution; verify dataset licence', 'audited_group_only', 5),
    ('cso', ('IE',), 'https://data.cso.ie/', 'PXStat JSON/CSV', 'table-dependent', 'published geography only', 'occupational groups; detailed unit coverage unverified', 'quarterly', 'CSO reuse licence', 'candidate_exact_source_unverified', 5),
    ('mospi', ('IN',), 'https://microdata.gov.in/', 'PLFS microdata', 'survey waves; methodological changes', 'national/state subject to sample size', 'NCO2015 3-digit in existing derivative', 'quarterly', 'Official access/registration terms; derivative ODbL separately', 'groups_only_official_microdata_access_review', 5),
    ('pbs', ('PK',), 'https://www.pbs.gov.pk/', 'LFS tables/microdata candidate', 'survey rounds', 'national/province; inspect tables', 'national/ISCO alignment unverified', 'quarterly', 'Availability and reuse conditions require validation', 'candidate_no_validated_exact_source', 5),
    ('ecb', tuple(COUNTRY_MAP), 'https://data-api.ecb.europa.eu/service/data/EXR/', 'SDMX CSV', 'daily working-day observations', 'currency pairs', None, 'daily', 'ECB statistical reuse attribution', 'existing_provider_not_new_connector', 4),
)


def catalogue():
    keys = ('id','countries','url','formats','history','geography','classification',
            'check_frequency','licence_and_restrictions','status','priority')
    return [dict(zip(keys, row), useful_new_observations=None,
                 estimate_reason='Requires a successfully downloaded catalogue and baseline diff; no invented count')
            for row in SOURCES]
