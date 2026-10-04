# Irlanda e Suíça — cobertura e aquisição oficial

Revisão de 4 de outubro de 2026; branch a partir de `main` `092bc2f` (inclui PR #41, sem retomar fiscalidade). Não existem AGENTS.md no checkout/ascendentes pesquisados. Ambiente Python 3.12 existente reutilizado. Relatório legível por máquina: [ie-ch-coverage-review.json](ie-ch-coverage-review.json).

## Antes/depois: não confundir código, staging e produção

| País/camada | Antes, código | Depois nesta PR | Anos/períodos e geografia |
|---|---|---|---|
| IE, entrada pública | 22 profissões, 22 valores de entrada | 22, sem novos salários verificados | março 2025, junho 2026 e período 2026 sem mês; serviço público irlandês, sem série regional |
| IE, CSO SES | 39 profissões com contexto de grupos; nove categorias, 18 estatísticas distintas | Sem alteração ou nova validação dos valores | 2022, nacional; médias/medianas horárias, não anualizadas |
| IE, ILOSTAT existente | 162 observações de grupos no snapshot | Sem alteração | 2020–2025; moedas/conceitos próprios, sem misturar CSO/public scales |
| CH, BFS ativo | Ficheiro ausente: zero observações BFS; 40 correspondências de interface para 22 grupos | Continua sem ativação: dados em staging privado | Nova aquisição cobre 2012, 2014, 2016, 2018, 2020, 2022, 2024 |
| CH, staging oficial novo | Zero nesta investigação | 10 640 células: 10 020 aceites, 430 incertas retidas para revisão, 190 suprimidas sem salário utilizável | 38 grupos, nacional + sete grandes regiões; cinco medidas por combinação (2 128 combinações grupo/ano/geografia) |
| CH, ILOSTAT existente | 162 observações de grupos no snapshot | Sem alteração | 2020–2025, não são dados adquiridos BFS |

As 40 profissões suíças têm contexto nacional mediano de 2024 no staging, mas **zero novas correspondências exatas profissão/salário**. Não contar 40 salários individuais nem multiplicar as estatísticas do mesmo grupo pelas profissões que o usam. Nacional: 1 320 células aceites + 10 incertas. Regional: 8 700 aceites + 420 incertas + 190 suprimidas.

A base local de desenvolvimento foi lida através de `app.bulk_coverage.database_rows`, usando SQLite somente leitura: zero linhas IE/CH nas tabelas salariais reconhecidas. Isso não prova ausência de dados produtivos nem contabiliza respostas do cache como observações validadas. Não foi fornecido inventário produtivo autorizado para esta tarefa. O ZIP anteriormente autorizado exclusivamente para Issue #25 não foi reutilizado. Para confirmar produção, operador pode gerar novo ZIP por «Exportar inventário salarial» e autorizar leitura para IE/CH. Nenhuma consulta à produção realizada.

## Irlanda: âmbito e lacunas

`app/ie_public_wages.py` contém referências de entrada, em EUR bruto/ano; não são média, mediana nem salário nacional representativo. A nota de Intern para doctor, de trainee solicitor para lawyer e de graduate architecture para architect deve acompanhar o valor. Chef II não é uma estatística do mercado de cooks. Arquitetura cita Forsa (sindicato), não uma entidade estatal: é código herdado, sem nova validação oficial nesta investigação. Não substituir uma escala histórica por uma escala atual só por manter o mesmo nome de grau.

Profissões com entrada no código: accountant, administrative_assistant, architect, auditor, cleaner, cook, cybersecurity_specialist, dentist, doctor, electrician, healthcare_assistant, it_technician, lawyer, nurse, pharmacist, physiotherapist, plumber, psychologist, secondary_teacher, security_guard, software_developer, teacher.

Sem entrada pública: agricultural_worker, automotive_mechanic, bus_driver, civil_engineer, construction_worker, data_analyst, financial_analyst, industrial_operator, manager, mechanical_engineer, preschool_teacher, receptionist, sales_assistant, supermarket_worker, truck_driver, waiter, warehouse_operator, welder. SES exclui agriculture; os outros grupos não resolvem automaticamente estas profissões exatas.

Consultas diretas CSO/PxStat, HSE, gov.ie e PublicJobs foram bloqueadas pelo proxy (403). `data.cso.ie` fornece a aplicação e configuração pública; a configuração confirma `https://ws.cso.ie/` como API. A aplicação HTML não contém salários e não foi tratada como tabela. EHA07/SES01 foram localizadores de investigação, **não tabelas ocupacionais confirmadas**; nenhuma célula foi importada. EHA deve ser verificada quanto a atividade económica versus profissão antes de qualquer uso.

Necessário obter: exportação original CSO SES por profissão com metadados/classificação e licença; tabela/PxStat original, não screenshot da aplicação. Para HSE, PDF completo de junho 2026 e escalas históricas com códigos, progressão, data de eficácia, horas/FTE e eventuais adicionais; para educação, circulares 0055/2026 e 0056/2026 originais com anexos. Fontes/URLs e respostas estão no [registo de acesso](ie-ch-source-access.json). Não há dados IE novos; não reconstruir valores a partir do código.

## Suíça: aquisição efetiva e conceitos

Fonte: [BFS/OFS ESS, tabela px-x-0304010000_205](https://www.pxweb.bfs.admin.ch/pxweb/en/px-x-0304010000_205/-/px-x-0304010000_205.px/). API comprovada: [metadados franceses](https://www.pxweb.bfs.admin.ch/api/v1/fr/px-x-0304010000_205/px-x-0304010000_205.px). GET e POST reais, completos, em 4 de outubro de 2026. JSON-stat 1 envolve `dataset`, com id/size dentro de dimension; a estrutura não é a suposta pelo workflow atual.

O original contém CH-ISCO-19 a um/dois dígitos. Foram selecionados apenas subgrupos documentados de dois dígitos, sexo total e idade total **explicitamente identificados**, sem fallback para primeira categoria. Grandes regiões: Région lémanique, Espace Mittelland, Nordwestschweiz, Zürich, Ostschweiz, Zentralschweiz, Ticino. Zürich designa a grande região, não salário municipal; os códigos não são cantões inferidos.

Salário bruto mensal padronizado em CHF, setor privado e público juntos; equivalente a 4 1/3 semanas de 40 horas. Referência: outubro dos anos pares. Inclui contribuições sociais do empregado, prestações em espécie, prémios/comissões regulares, adicionais por turnos/domingo/noite e 1/12 do 13.º salário/pagamentos especiais anuais; exclui prestações familiares/filhos. Mediana, P10, P25, P75 e P90 separados. Não são médias, líquido, pagamento contratual mensal nem 12 meses efetivos de folha salarial. Não anualizar nem interpolar anos ímpares.

Footnotes oficiais: 2012–2018 foram recalculados em CH-ISCO-19 para comparabilidade da série 2012–2024; data da base 24-02-2026. O cabeçalho JSON-stat declara `updated=2019-11-08T07:30:00Z`, inconsistente com a série: ambas as datas foram preservadas, sem usar a primeira como prova de atualização 2024. A classificação/anos/valores foram conferidos diretamente nos originais; 10 640 células e respetivos índices/flags foram reconferidos por cálculo independente dos strides.

`X` significa supressão por proteção de dados, `...` ausência, `( )` incerteza estatística. Valores incertos ficam `value=null`, mantendo `original_value` privado e flag para revisão. Não são promovidos para aumentar cobertura; uma mediana ausente/incerta não produz disponibilidade nem fallback histórico silencioso. As cautelas dos títulos genéricos existentes (manager, warehouse_operator, data_analyst, etc.) mantêm-se. Não validar equivalências exatas através destes grupos.

## Arquitetura e entrega segura

Reutilizado `app/ch_bfs_wages.py` e o modelo snapshot existente: seleção revista, normalização JSON-stat, validação de originais por SHA-256, completude, índices, dimensão, medidas, flags e duplicados. Leitor permite inspeção explícita por ano/grande região, preservando chamada/API existente. Não foi acrescentado outro gestor, tabela SQLite, importador salarial genérico ou alteração aos endpoints.

O staging privado tem 4 001 355 bytes; SHA-256 `074cd304aa906af606479a8b7fd9b8d6f9d4bd86b24f7a389cf8589f06497dc5`. O original POST tem 66 715 bytes e SHA-256 `1188ba467a970ae19cfcb7dcbc1c99b14624aeaf2de5a5f6b4ec4adf6dba6301`; query/metadados/acquisition date no relatório JSON. Originais e staging estão fora de Git e do arquivo de deployment. O marcador `private_staging_only` impede ativação acidental se este snapshot for colocado no caminho runtime padrão.

A API publica `© OFS`, o que **não constitui licença de redistribuição validada**. Os pedidos a BFS usage-rules e opendata.swiss foram bloqueados; falta confirmar termos oficiais, licença aplicável e atribuição. A tabela/número de versão e atribuição OFS estão preservados. Sem essa prova, os valores não são distribuídos nesta PR nem ativados. Isso não é uma alegação de que a reutilização seja proibida.

O workflow herdado `import-ch-bfs-wages.yml` procura dimensões inglesas, latest-only, total por fallback e ignora flags/layout JSON-stat 1: não usar para publicar esta aquisição. Nesta tarefa não foi disparado nem ativado qualquer workflow de aquisição. As funções desta PR são a base para substituir esse bloco após validar licença e rever a distribuição; não repetir download para recuperar este staging. Os outros mecanismos bulk/Data Manager ficam intactos.

## Instruções para o operador, sem terminal

1. Abrir a PR e rever relatório/contagens. Esta PR é implementação de validação e aquisição privada, **não contém um lote salarial publicável**.
2. Fornecer os originais/licença IE e condições oficiais BFS através da conversa ou anexos, com URL/data; não copiar salários de exemplos. Os originais suíços já adquiridos não precisam de nova descarga.
3. Exportar e autorizar inventário atual no Data Manager se for necessário confirmar cobertura produtiva; isso é somente leitura.
4. Não carregar este staging no botão de pacotes salariais: tem 4 MB, é snapshot de contexto e **não** o formato de publicação bulk de 2 MiB. O bulk atual só projeta as tabelas US/CA/NL autorizadas; não forçar CH/IE nessas tabelas.
5. Quando licença e revisão forem concluídas, a via prevista para BFS é snapshot validado `data/ch_bfs_wages.json` distribuído com código, através de PR/release revista e do controlo existente «Atualizar API». Não requer importação de BD. Isso exige entrega posterior autorizada; esta tarefa não faz merge, atualização do cPanel ou deployment. Nunca copiar o ficheiro privado diretamente para produção nem retirar o marcador para contornar a revisão.

## Testes

Os testes de parsing usam dados sintéticos apenas para falhas/fronteiras; não são substitutos da aquisição. A validação live foi efetuada separadamente contra os originais reais, com checksums e as 10 640 células conferidas. Testes específicos cobrem histórico/regiões, totais ausentes, supressão/incerteza, índices/labels/dimensões inesperados, valores inválidos, hashes e duplicação, regressão dos endpoints existentes. Resultado final registado após a suite completa.

Resultado final: **1 026 testes aprovados, zero falhados, 20 subtestes aprovados**; 29 testes específicos aprovados. Persiste um aviso herdado Starlette/httpx. `git diff --check` aprovado. Arquivo real construído pelo mecanismo existente e instalado isoladamente: respostas WSGI IE/CH válidas, entrada IE preservada e staging privado ausente. CI base `main` aprovado no run 37239871986; verificar também CI da PR antes de integração futura.
