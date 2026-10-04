# Issue #25 — reconciliação salarial offline

Auditoria em **4 de outubro de 2026 (Europe/Lisbon)**, PR #26, com autorização do
operador exclusivamente para leitura/normalização/comparação/relatório. **Não há
primeiro pacote elegível:** todos os dados representáveis pelo mecanismo actual
já constam do export. Não preparar um pacote só para repetir duplicados.

## Entrada validada e limites

ZIP autorizado SHA-256
`9cd8b2205d1f746625dae4d378db29298899f640ebb79890a68722fe5206aef0`;
exportado **2026-10-03 22:10:35 UTC / 23:10:35 em Lisboa**. Schema
`earnwage-salary-table-inventory-v1`, três tabelas completas no âmbito declarado:
1 560 linhas `us_oews`, 85 `north_america_wages`, 2 493 `ca_province_wages`;
**4 138 linhas**, 2 184 026 bytes JSON. SQLite reportado 3.53.4, sem WAL no export.

Verificados hash externo, CRC ZIP, nomes únicos/permitidos, ausência de symlinks,
encriptação e extras, limites, schema/colunas/PK, chaves JSON sem duplicação,
valores finitos, checksums/tamanhos individuais, timestamps e totais. Não foram
fornecidos/solicitados tokens ou caminhos de produção. O ZIP/raw JSON e o modelo
SQLite privado reconstruído **apenas do export** ficaram fora do Git. Nenhuma
consulta directa à produção foi efectuada; os resultados não afirmam estado live
nem abrangem tabelas fora destas três.

## Staging confirmado, sem novas aquisições

| Fonte | Bytes | SHA-256 antes e depois da análise |
|---|---:|---|
| BLS OEWS | 2 462 720 000 | `6be2fe4ae98659a031460a09234d1b334ebd47d63d0b104948fdb025f1ecc069` |
| Job Bank | 51 671 040 | `c48c29339823aa74b76fc2193b8126fc69207b3b53aa8b4dbcb45cdd03611a04` |

Últimos runs de todos os releases `complete`/`live_bulk`. 868 201 valores aceites
BLS (SOC2018, 2021–2025) e 14 018 Job Bank (NOC2021, release 2025). **13 565 versões
BLS em quarentena**, 28 830 BLS e 5 074 Job Bank em falta continuam excluídos.
Não houve descarregamento, importer, escrita no staging ou publicação.

A comparação inversa encontrou **176 identidades BLS existentes no export mas
apenas em quarentena no staging**, sem versão aceite actual. Não são propostas
de revisão numérica entre valores aceites, nem dados a eliminar/substituir.
No Job Bank não há identidades normalizadas existentes fora do staging aceite.
As 20 860 identidades normalizadas correspondem a 20 684 duplicados aceites e
a estas 176 observações em quarentena; a reconciliação preserva todas.

## Resultado por fonte e âmbito

Contagens abaixo são **células estatísticas físicas**, não linhas SQL nem
profissões. «Ausentes» significa ausentes nas identidades comparáveis das três
tabelas exportadas; não significa publicáveis ou inexistentes noutra base.

| Fonte/âmbito | Aceites no staging | Duplicados | Ausentes no export | Revisões numéricas |
|---|---:|---:|---:|---:|
| BLS nacional | 1 632 | 1 632 | 0 | 0 |
| BLS regional | 866 569 | 16 558 | 850 011 | 0 |
| **BLS total** | **868 201** | **18 190** | **850 011** | **0** |
| Job Bank nacional | 219 | 73 | 146 | 0 |
| Job Bank provincial/territorial | 2 421 | 2 421 | 0 | 0 |
| Job Bank regiões económicas | 11 378 | 0 | 11 378 | 0 |
| **Job Bank total** | **14 018** | **2 494** | **11 524** | **0** |

BLS nacional histórico: **324 células em 2021, 326 em 2022, 326 em 2023 e 326 em
2024**, todas duplicadas; 330 em 2025 igualmente duplicadas. O primeiro pacote
software_developer/May 2021 (`dbf36d12…f60c9`) foi confirmado pela identidade,
metadados e igualdade das 12 medidas; já está presente, não é novo candidato.
Job Bank mantém 2023–2024 como período único, não como dois anos.

### Incompatibilidades e preview local

- As **850 011 células BLS regionais ausentes** não podem ser publicadas pela via
  actual: staging histórico não preserva `prim_state` completo para a projecção
  regional. Há 866 569 células regionais aceites no total; o mecanismo exclui-as
  todas, incluindo as já existentes. Não inferir metadados nem voltar a adquirir
  arquivos nesta tarefa; qualquer futura revisão usará as fontes já guardadas.
- As **146 células Job Bank nacionais ausentes** são medidas fora de mean/median,
  não suportadas pela projecção nacional. As **11 378 regiões económicas** não
  têm tabela/API de destino no modelo actual. Estes dados não são salários
  provinciais/nacionais substitutos e não devem ser publicados nesses âmbitos.
- A normalização produziu **20 860 identidades**, usando o normalizador existente,
  com provider/dataset, classificação, geografia, período, medida/unidade/moeda,
  indústria/ownership/o_group e versão NOC. Aliases compatíveis são deduplicados;
  divergências numéricas entre aliases abortam. As fontes/URLs literais originais
  continuam no export privado e no confronto com o modelo de destino.
- O protocolo normalizado tem `scope: partial`: as **10 linhas US Table 1** de
  `north_america_wages` não explicitam indústria/ownership. Foram examinadas
  separadamente para sobreposição/linha protegida, sem inventar dimensões nem
  misturar proveniências. São nacionais de 2025; não alteram a conclusão de zero
  novos históricos. Não se usa ausência num âmbito ambíguo como prova de novidade.
- Preview **só local**, contra o modelo das tabelas autorizadas, com o mecanismo
  existente: **BLS 140 linhas-alvo duplicadas; CA 2 568 duplicadas; 0 inserções e
  0 linhas protegidas**. Correspondem a 1 632 e 2 494 células representáveis.
  Aliases canadianos originam várias linhas de destino por célula; esta diferença
  não aumenta observações independentes. Não houve execução de publish/rollback.

## Cobertura antes/depois e profissões restantes

A cobertura nacional do export é **US 29/40 profissões** (28 SOC; accountant e
auditor partilham código), **CA 38/40**. Regional: os mesmos 29 e 38 IDs. União
US/CA: **67/80 pares**, inalterada; **zero novos pares** com este staging. Isto
não confirma a cobertura global 164/560, pois este ZIP não exporta as restantes
fontes/países. Mesmo uma futura publicação regional não acrescentaria pares
inteiramente novos nestes dois países.

US sem mapping aprovado/dados nestas tabelas: agricultural_worker, cleaner,
cook, data_analyst, doctor, industrial_operator, manager, psychologist,
supermarket_worker, teacher, warehouse_operator. CA: agricultural_worker e
manager. Não alargar mappings ambíguos nem usar grupos como salários individuais.

## Próximos passos e autorização

**Lista de pacotes elegíveis: vazia.** Não se gerou ficheiro de pacote nem
checksum candidato fictício. Nenhuma importação/publicação deve decorrer desta
reconciliação. Próximo trabalho útil: validar e recuperar metadados regionais BLS
nos arquivos já existentes; desenhar representação independente das regiões
Job Bank e das medidas nacionais adicionais, com testes/contratos revistos.
Isso exige tarefa/PR específica, não está implementado aqui.

Para futura publicação, repetir export actualizado, confronto das três tabelas,
verificação de conflitos/duplicados, backup/ensaio de recuperação e aprovação
explícita do pacote/checksum. Referências operacionais:
[PHASE4E.md](PHASE4E.md), [PHASE4F.md](PHASE4F.md),
[PHASE4I.md](PHASE4I.md). Não efectuar merge/deployment para publicar dados.

### Plano de investigação dos restantes países (sem aquisição)

Este ZIP não permite confirmar ausência produtiva global nesses países. As fontes
abaixo são candidatas para auditoria própria, não novos dados verificados:

| Prioridade | País/fonte oficial candidata | Validação obrigatória antes de salário individual |
|---|---|---|
| 1 | PT — GEP/Quadros de Pessoal | CPP detalhada, universo assalariado, bruto/período; acesso/licença de microdados; tabelas de grupos não bastam. |
| 1 | BR — Ministério do Trabalho/RAIS | CBO2002 detalhada, vínculo/remuneração mensal, cobertura estadual/nacional, mappings e acesso/licença oficiais. |
| 2 | ES — INE/Encuesta de Estructura Salarial | CNO detalhada e microdados; CNO major groups da tabela 28186 não equivalem às 40 profissões. |
| 2 | IE — CSO/estatísticas de remunerações | Nível ocupacional efectivo, universo/medida e supressão; confirmar dataset/códigos antes de prometer salários exactos. |
| 2 | CH — FSO/LSE | CH-ISCO detalhada e disponibilidade; grupos públicos CH-ISCO19 não substituir profissões individuais. |
| 2 | IT — Istat/SES | CP detalhada, universo, remuneração/unidade e acesso; excluir agregados profissionais amplos. |
| 3 | IN — MoSPI/PLFS | NCO2015, amostra/pesos/cobertura e classe de trabalhador, microdados/licença; grupos de 3 dígitos não são equivalências automáticas. |
| 3 | PK — PBS/Labour Force Survey | Classificação ocupacional nacional, rendimento/período, amostra e acesso; rejeitar equivalências inferidas. |

Usar [catálogo existente](README.md) e auditorias de fonte existentes;
não alterar PR #13, fiscalidade, câmbios, indicadores económicos, Android ou
workflows. Não foram activadas agendas.

## Reprodutibilidade e testes

A validação e avaliação de alvo reutilizaram o procedimento privado Phase 4G/5A,
`app.salary_inventory_export`, `app.bulk_publication.build/preview`,
`app.bulk_salary_coverage.baseline_index` e `app.bulk_inventory_export.compare`.
A única alteração do comparador expõe opcionalmente as mesmas linhas normalizadas
para evitar duplicar a lógica ao passar um export autorizado ao comparador.
Leituras de staging `mode=ro`; modelo de preview isolado derivado só do inventário.

[Resumo agregado com hashes](issue25-reconciliation-summary.json): valores por
fonte/geografia/ano, contagens do preview, testes e blockers; sem inventário raw,
datasets, bases ou configuração privada no Git. Para reproduzir: validar ZIP
Phase 4F, usar os três JSON autorizados no normalizador existente, escrever o
protocolo `earnwage-observation-inventory-v1` apenas em pasta privada e executar
`compare` para cada staging, com a referência de autorização. Avaliar os alvos
via `build/preview` apenas no modelo isolado; nenhum exporter/importer produtivo.

**642 testes aprovados, 0 falhas**, 87,11 s; um aviso de depreciação herdado
Starlette. Dois testes novos cobrem união/deduplicação de aliases, períodos
plurianuais, conflitos, fontes diferentes e reutilização do protocolo existente.
Suite dirigida: 63 aprovados. GitHub Actions registado na PR após conclusão.
