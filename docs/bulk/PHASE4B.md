# Fase 4B — expansão salarial bulk

Implementação na branch `feat/bulk-data-coverage`, PR #14, independente da PR
fiscal #13. Data de aquisição: **3 de outubro de 2026**. Toda a aquisição decorreu
em staging privado local, sem ligações/escritas às bases produtivas, sem alterações
Android, token administrativo, cálculos económicos/fiscais ou deployment.

## Aquisição live validada

| Fonte | Releases | Linhas de origem validadas | Valores aceites | Versões em quarentena | Valores em falta preservados |
| --- | --- | ---: | ---: | ---: | ---: |
| BLS OEWS | 2021–2025, SOC2018 | 2 057 509 | 868 201 | 13 565 | 28 830 |
| Job Bank | 2025, NOC2021 | 44 376 | 14 018 | 0 | 5 074 |
| Total | | 2 101 885 | **882 219** | **13 565** | **33 904** |

São observações físicas por código/geografia/período/medida/unidade/dimensões;
alias accountant/auditor não duplicam salários. Outras profissões/âmbitos de indústria
ou propriedade são lidos/validados mas excluídos da selecção EarnWage. No BLS,
75 883 linhas seleccionadas originam 910 596 células, incluindo quarentena e
supressão; no Job Bank, 3 182 linhas seleccionadas originam 19 092 células.

Reutilização: parser XLSX/ZIP BLS existente, leitor provincial Job Bank existente,
Downloader, cache com SHA-256, ledger SQLite, checkpoints, política de refresh e
worker da Fase 4. O índice de séries inclui dimensões adicionais e evita varrimentos
por país/indicador para cada salário. Nenhum sistema de importação paralelo.

A repetição revalidou os datasets e inseriu **zero novas observações**. O BLS 2022
contém um duplicado exacto: linhas de dados 319 143 e 319 144, código `43-5053`,
MSA `33460`, MN; é registado e excluído da contagem adicional, sem efeitos nos
códigos EarnWage. Níveis `broad`/`detailed` distintos não são falsos duplicados.
Identidades com valores divergentes são rejeitadas. Os erros de validação exploratória
ficam no histórico; as últimas execuções de todos os releases são `complete`.

Fontes, hashes, bytes, datas UTC exactas e contagens por release estão em
[phase4b-evidence.json](phase4b-evidence.json). Detalhes metodológicos:
[BLS](BLS.md) e [Job Bank](JOB_BANK.md). Fixtures pequenas e autênticas têm
manifesto em `tests/fixtures/bulk/salary_provenance.json`; testes de amostras não
são contados como downloads live.

## Cobertura efectivamente acrescentada face à baseline disponível

A comparação usa apenas três snapshots oficiais cuja identidade é reconstruível:
`us_oews_curated.json`, `north_america_wages.json` e `ca_province_wages.json`.
São 19 558 identidades não nulas na baseline; 176 não figuram no universo aceite
actual e estão em quarentena BLS, sem serem eliminadas dos snapshots/API existentes.
A comparação considera os valores
aceites actuais, excluindo quarentena e salários indisponíveis da cobertura verificada.

| Fonte | Observações novas | Revisões numéricas | Duplicados da baseline | Histórico anual novo | Registos regionais aceites | Regionais novos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BLS | 851 313 | 0 | 16 888 | 693 195 | 866 569 | 850 011 |
| Job Bank | 11 524 | 0 | 2 494 | 1 716 | 13 799 | 11 378 |
| Total | **862 837** | **0** | **19 382** | **694 911** | **880 368** | **861 389** |

BLS reforça **29 das 40 profissões**, agora com histórico 2021–2025 e estados,
territórios, MSA e áreas não metropolitanas. Job Bank reforça **38 das 40**, com
nacional, 13 totais provinciais/territoriais e regiões económicas. Há **zero pares
país/profissão inteiramente novos face a estes snapshots**: os 67 pares já existiam;
o ganho é profundidade temporal/regional e medidas publicadas adicionais.

Não foram inferidos códigos para as 11 profissões norte-americanas restantes
(agricultural_worker, cleaner, cook, data_analyst, doctor, industrial_operator,
manager, psychologist, supermarket_worker, teacher, warehouse_operator) nem para
agricultural_worker/manager no Canadá. Os mapeamentos herdados podem ter âmbito
mais estreito ou partilhado; não se afirma equivalência universal entre profissões.

«Histórico anual novo» conta apenas períodos exactos YYYY anteriores a 2025,
ausentes da baseline. **2023–2024 continua um período único**. Valores de origem
fiscal/inquérito podem ter definições diferentes; preservar a fonte original não
autoriza comparações de rendimento líquido ou poder de compra internacional.
Códigos geográficos publicados podem mudar de definição entre releases; não se
assume equivalência com cidades ou seletores ISO nem se mistura nacional/regional.

## Produção e segurança

**Não foi fornecido um export autorizado de produção.** A cobertura real e as
respectivas diferenças ficam `not_provided`, com contagens `null`. Os números
anteriores são exclusivos da baseline local e não provam novidade em produção.

O protocolo [INVENTORY_EXPORT.md](INVENTORY_EXPORT.md) permite ler um JSON local
explicitamente autorizado, limitado a 100 MiB, sem symlinks, agregado insuficiente,
identidades duplicadas, números não finitos ou dimensões ignoradas. A leitura do
staging usa SQLite `mode=ro`; não consulta variáveis/caminhos produtivos ou endpoints
administrativos. Comparação exacta Decimal; geografia, unidade, moeda, classificação,
medida e dimensões participam na identidade. Exportações parciais são assinaladas.

Para efectuar a comparação: obter do operador um export conforme o protocolo,
com autorização e âmbito/data explícitos. Não acrescentar esse export ao Git.
A referência textual de autorização no CLI não substitui autorização do proprietário.

## Quarentena original e tamanho da PR

Foram revistos/classificados **todos os 257 casos** da Fase 4:

| Triagem para avaliação manual | Casos |
| --- | ---: |
| Mortalidade/conflitos: volatilidade ou alterações de definição | 124 |
| Unidade monetária/câmbio, incluindo remuneração Eurostat | 36 |
| Direcção/escala da inflação | 27 |
| Inquéritos, definições e séries | 63 |
| Flag oficial Eurostat `b`: quebra de metodologia | 7 |

Há 250 variações numéricas e sete quebras explícitas. A triagem não identifica
automaticamente a causa verdadeira. Todos continuam em quarentena; **zero aprovados
automaticamente**. A sequência portuguesa Eurostat de remuneração líquida com quebra
e variação de ordem de grandeza merece prioridade. Valores adjacentes são contexto,
não prova independente. O [CSV de revisão](quarantine-review.csv) conserva os 257
casos com fonte, hash, valor, período, comparação e decisão de retenção.

Foram retirados cerca de 4 MB de JSON/dashboards/relatórios gerados do diff. O CSV
pequeno de revisão e a evidência compacta permanecem para permitir inspecção da PR.
Workbooks, ZIP, CSV completo, SQLite e dashboards completos ficam fora do Git.

## Reproduzir o dashboard

```bash
.venv/bin/python -m scripts.bulk_inventory \
  --staging /caminho/privado/bls/staging.sqlite3 \
  --staging /caminho/privado/job-bank/staging.sqlite3 \
  --output docs/bulk/generated/phase4b
```

Opcionalmente juntar `--insights-db`/`--acquisition-report` da execução WDI/Eurostat.
Para comparação produtiva, acrescentar `--production-inventory export-autorizado.json`
e `--inventory-authorization referencia-do-operador`. O dashboard inclui pares,
períodos, origens, datas, medidas, regiões, quarentena e diferenças da baseline;
execuções incompletas e modos `sample_test`/não verificados são identificados.
Um último import incompleto impede promoção e não aparece como cobertura verificada.

Configuração manual: Python/dependências existentes; directório privado com espaço
para downloads e ledger (nesta validação, alguns GB). Autorizar HTTPS público para
`www.bls.gov`, `open.canada.ca` e `opencanada.blob.core.windows.net`. O destino Job
Bank é limitado ao prefixo público `/opengovprod/resources/`; queries SAS temporárias
não são guardadas no URL resolvido nem expostas nos logs do worker. Sem novos segredos,
cron, activação de deployment ou alteração de configuração produtiva.

## Testes e limites restantes

**Suite completa: 424 testes aprovados, zero falhados.** Preservados os 369 anteriores;
55 testes novos cobrem parsers, medidas, supressões, anos errados, limites geográficos,
dimensões inesperadas, duplicados/conflitos, regressões após supressão, inventário
autorizado, leitura sem escrita, dashboard/baseline e proveniência autêntica.
Mantém-se um aviso herdado Starlette TestClient/httpx; dependências/deployment não
foram alterados para o eliminar.

Limites explícitos: releases BLS anteriores a 2021 continuam pendentes de validação
SOC 2010/híbrida e layouts XLS/XLSX; Job Bank só tem o release 2025 registado, apesar
de o catálogo publicar edições anteriores. Quarentena nova BLS requer revisão antes
de promoção. Valores ausentes, grupos incompatíveis e profissões sem mapeamento não
são estimados. Não foi publicada a aquisição em endpoints produtivos: os contratos
FastAPI/WSGI existentes permanecem, e não houve merge ou deploy.
