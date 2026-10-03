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

## Phase 4C — publicação segura (2026-10-03)

### Auditoria de Actions

Foram revistos **35 workflows**, incluindo chamadas a módulos/scripts, permissões,
triggers e comandos de publicação. O workflow herdado
`import-canada-province-wages.yml` fazia `git rebase origin/main` seguido de
`git push origin HEAD:main` a partir de triggers `push` por caminhos, inclusive
numa feature branch. Podia publicar também o histórico da branch. Não era um
canal seguro de revisão. Nove outros workflows tinham `git push` equivalente.

Os dez passam a ter aquisição/validação com `contents: read`, checkout sem
credenciais persistentes e um **job de escrita separado**, limitado a execução
manual, no repositório original e com ref `main`. Preservam-se flags manuais já
existentes e jobs de leitura. O job testa a suite completa sobre o dataset proposto
e cria via GitHub API uma branch `data-review/<run>-<attempt>` e PR. A árvore tem
como base o SHA exacto do `main` que originou o dispatch; se este avançou, aborta.
Só ficheiros JSON de dados explicitamente autorizados podem mudar. Não se copiam
commits da feature branch nem se actualiza qualquer ref `main`.

Ver [auditoria por workflow](workflow-publication-audit.json).
O workflow de refresh produtivo continua a usar exclusivamente o Data Manager
existente e a sua variável de activação. Nenhum cron foi activado. O sistema de
SSH/deployment não foi modificado. `actionlint 1.7.12` aprovou **34 workflows**,
incluindo os dez alterados. No 35.º, `deploy-production.yml` inalterado, assinalou
`if-cond` por whitespace em torno de `${{ }}` num bloco `if: >`. Os cinco últimos
runs consultados estavam `skipped`. Este alerta requer revisão separada; não se
alteraram condições, segredos ou activação do deployment nesta fase.

Antes de usar as novas publicações, um administrador deve permitir ao
`GITHUB_TOKEN` criar PRs nas definições Actions do repositório. PRs criados com esse
token podem não desencadear CI automaticamente; validar os checks antes de merge.
A publicação é uma proposta revista em Git, não um import produtivo. Ficheiros
maiores que 4 MiB (ou 10 MiB no total) são recusados por esta via e exigem revisão
de estratégia de artefactos.

### Quarentena BLS: análise completa, sem aprovações automáticas

Foram percorridas **13 565 versões/observações**, agrupadas conjuntamente em
**3 253 grupos** por ano, SOC, nível geográfico, medida/unidade, motivo e magnitude.
O relatório agregado e **28 exemplos estratificados** estão em
[bls-quarantine-summary.json](bls-quarantine-summary.json). O relatório completo é
reproduzível e fica ignorado em `docs/bulk/generated/`, não inflaciona o PR.

| Dimensão | Resultado |
| --- | --- |
| Releases | 2022: 3 863; 2023: 3 565; 2024: 2 781; 2025: 3 356 |
| SOC | 28 códigos detalhados SOC 2018; nenhum grupo amplo promovido |
| Geografia | Estados: 751; territórios: 117; metropolitanas: 8 640; não metropolitanas: 4 057; nacional: 0 |
| Motivo | 13 565 `unexpected_revision_or_temporal_variation` |
| Variação absoluta | >30–50%: 9 898; >50–100%: 3 208; >100%: 459 |
| Aprovações após revisão | **0**; todas permanecem em quarentena |

A magnitude é recalculada contra a observação **anterior finita mais próxima** da
mesma série/dimensões, incluindo valores oficiais em quarentena. É uma métrica
retrospectiva, não uma reconstrução presumida do comparador original do importador.
Nenhuma ficou <=30% nesta comparação. Os exemplos são extremos estratificados por
medida/unidade, ano/geografia e magnitude; não são uma amostra aleatória estatística.

Há concentração em dentistas (2 557), advogados (1 620) e empregados de mesa
(1 289), bem como nos percentis 10/90 (7 263 células somadas). Hora/ano mantêm-se
separados, embora possam reflectir o mesmo movimento da distribuição original.
A ausência de alertas nacionais e a concentração regional são factos observados;
não se atribui causalidade individual apenas por correlação.

A [FAQ oficial BLS](https://www.bls.gov/oes/oes_ques.htm), secção de comparabilidade,
afirma que o BLS **não encoraja análise de séries temporais OEWS** e que alterações
geográficas podem tornar séries do mesmo código não directamente comparáveis.
Documenta também a mudança de intervalos salariais para taxas exactas em maio de
2022 e a publicação de novos percentis superiores em 2025. O
[Handbook de estimação](https://www.bls.gov/opub/hom/oews/calculation.htm) documenta
MB3, modelação e seis painéis em três anos. Estes factores sustentam dúvidas sobre
um corte temporal genérico de 30% como certificado de erro salarial. Não validam,
por si, cada observação sinalizada. Por isso **não se relaxou o limiar nem se aprovou
quarentena** para aumentar cobertura. Revisão futura deve confrontar definições
geográficas por release, quantis/variância e o registo original verificável.

```bash
python scripts/bls_quarantine_review.py \
  --staging /ABSOLUTO/PRIVADO/bls/staging.sqlite3 \
  --output docs/bulk/generated/phase4c/bls-quarantine.json
```

### Profissões em falta

As **11 US e duas CA** foram registadas individualmente em
[missing-occupation-review.json](missing-occupation-review.json), com códigos
candidatos, títulos oficiais e motivo da decisão. A classificação original
[SOC 2018, definições BLS](https://www.bls.gov/soc/2018/soc_2018_definitions.pdf)
foi descarregada e verificada nesta fase; checksum no relatório. Os títulos
EarnWage são genéricos e abrangem vários códigos com âmbito distinto: por exemplo,
limpeza doméstica e de edifícios, diferentes cozinheiros, diferentes especialidades
médicas e diferentes tarefas de armazém. Não há autorização estatística para
escolher só um código e apresentar o salário como se cobrisse toda a profissão.

No Canadá, o CSV oficial já adquirido confirma títulos separados para trabalho
agrícola e gestão. As páginas originais NOC de Statistics Canada/ESDC continuam
inacessíveis nesta sessão (`ProxyError`); títulos não substituem definições de
funções. Foram acrescentados ao **rascunho** de configuração cloud, preservando os
restantes destinos, `www.statcan.gc.ca`, `www23.statcan.gc.ca` e `noc.esdc.gc.ca`.
O acesso voltou a falhar no teste; a gravação do rascunho não prova activação runtime.
Ambos os mapeamentos ficam pendentes, sem aprovação.

**Novos pares país/profissão verificados: 0.** Mantêm-se 29 US e 38 CA (67 pares
existentes); os 13 em falta exigem âmbito ocupacional mais preciso e/ou validação
oficial, não substituição por grandes grupos.

### Publicação eficiente: ensaio exclusivamente local

Ver [procedimento operacional](PUBLICATION.md) e
[evidência do ensaio](publication-validation.json). Os componentes reutilizam o
staging Phase 4B, tabelas salariais existentes, lock/autenticação/backups do Data
Manager e ferramenta de recuperação já existente. Novos endpoints administrativos
ficam **desactivados por omissão**, exigem checksum exacto, token existente e
confirmação explícita. Nenhum endpoint público salarial muda.

Prepararam-se **cinco pacotes**, com **4 126 células** aceites e **3 464 907 bytes**:
BLS nacional 1 632; Job Bank nacional/provincial 2 494. O limite é 1 000 células e
2 MiB por pedido. Não se transferem os ZIP completos nem o ledger de vários GB.
As células de uma linha OEWS não são divididas entre pacotes. Cada base, incluindo
WAL, tem limite de 256 MiB nesta via; limites e lock de 5 segundos protegem o
hosting partilhado. Schema e chaves primárias são verificados antes da escrita.

O ensaio criou bases SQLite locais apenas com snapshots Git: 1 448 linhas OEWS,
85 nacionais norte-americanas e 2 493 provinciais canadianas. Os cinco pacotes:

- Inseriram **112 linhas OEWS históricas** que faltavam na cópia local.
- Identificaram **2 596 linhas duplicadas**, incluindo aliases ocupacionais CA.
- Encontraram **0 conflitos** nessa baseline. Testes adicionais comprovam protecção
  de conflitos/NULL existentes e recusa de sobrescrita.
- Passaram repetição idempotente, backups frescos, recuperação para directório
  novo e rollback integral das únicas linhas inseridas. As contagens iniciais
  foram repostas e `PRAGMA integrity_check` devolveu `ok`.

As contagens de linhas SQL não são as contagens de células salariais ou pares:
uma linha OEWS contém várias medidas e códigos partilhados CA geram mais de uma
linha por célula oficial. Não existe inventário produtivo autorizado, pelo que
estes números **não representam diferenças efectivas em produção**.

Mantêm-se fora do pacote: 866 569 células BLS regionais (metadados históricos
`prim_state` original incompletos), 11 378 Job Bank de regiões económicas (sem modelo
API/tabela existente equivalente) e 146 medidas nacionais CA fora do contrato
média/mediana. Não são descartadas nem convertidas em dados nacionais: permanecem
no staging e no dashboard com as unidades e proveniência originais.

O dashboard pode ser reproduzido com `--publication-review docs/bulk/phase4c-review.json`
além dos argumentos Phase 4B. Inclui a análise de quarentena, pares novos, pacotes,
âmbitos excluídos e ensaio local, mantendo a ausência de inventário produtivo explícita.

Pré-requisitos produtivos: integração revista, exportação produtiva autorizada,
validação de compatibilidade e recursos, transferência privada dos pacotes revistos,
backups/recuperação testados pelo operador e activação **manual** da via Data Manager.
Nenhum deles foi activado remotamente nesta entrega. Não houve merge, deploy,
alteração de Android, dados económicos, token ou bases de produção. PR #13 continua
independente.

### Validação final Phase 4C

**455 testes aprovados, 0 falhados**, incluindo todos os 424 anteriores e 31 novos.
Cobertura nova: gates de workflows/branches, árvore do PR limitada a dados, recusa
quando `main` avança, classificação completa da quarentena read-only, pacotes e
checksums, supressões, schema/PK, limites, autenticação/confirmacão, backup antes de
escrita, idempotência, conflitos protegidos, atomicidade, rollback após edições,
recuperação e dashboard com distinção explícita entre ensaio local e produção.
Mantém-se **um aviso herdado** Starlette TestClient/httpx. `pip check` passou.
YAML dos 35 workflows foi analisado; `actionlint` validou os 34 sem o alerta de
whitespace herdado no deployment, já descrito acima. O lint foi executado sem
integração externa ShellCheck/Pyflakes; não se afirma que esses analisadores passaram.
