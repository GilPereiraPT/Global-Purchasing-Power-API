# Expansão salarial — Reino Unido, Alemanha, França e Países Baixos

Investigação de 4 de outubro de 2026, a partir da main `d2e0fdb`.
Não houve importações, publicação, alterações de salários, fiscalidade, câmbios,
Android ou deployment. Os ficheiros oficiais descarregados e a seleção para
revisão ficaram numa pasta privada fora do Git. Não há pacotes autorizados.

## Resultado e âmbito

| País | Profissões no snapshot | Lacunas entre as 40 | Observações no snapshot | Definição |
| --- | ---: | ---: | ---: | --- |
| Reino Unido | 26 | 14 | 52 | Média/mediana anual bruta, ASHE 2025 provisório |
| Alemanha | 27 | 13 | 27 | Mediana mensal bruta Entgeltatlas 2025, âmbito específico da profissão/nível |
| França | 23 | 17 | 23 | Média líquida mensal EQTP, assalariados do setor privado, 2024 |
| Países Baixos | 21 | 19 | 21 | Mediana horária bruta, grupos BRC aprovados, 2024/2025 |
| **Total** | **97/160** | **63** | **123** | Conceitos diferentes, preservados separadamente |

Contagens obtidas dos snapshots e confrontadas com `app.bulk_coverage.build_report`,
sem bases fornecidas. Não representam uma medição da produção, nem garantem
correspondência universal entre cada grupo nacional e uma profissão individual.
O inventário salarial autorizado na Issue #25 abrange somente as três tabelas
US/CA; não serve como baseline destes países. Ausência no Git não prova ausência
na fonte ou na produção. Não se descobrem bases através das variáveis do servidor.

A [matriz das 63 lacunas](europe-missing-occupations.csv) contém uma decisão e
próxima verificação por combinação. Os códigos candidatos são pistas de revisão,
**não novos mappings aprovados**. O [relatório de evidência](europe-coverage-review.json)
regista hashes dos snapshots, tentativas de acesso, hashes dos downloads, versões,
contagens, igualdade dos dados existentes e limites. Novos pares aprovados: **0**.

## Reino Unido — aquisição real e validação

Fonte: [ONS ASHE Table 14, 2025 provisional](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/occupation4digitsoc2010ashetable14/2025provisional).
O ZIP oficial completo foi descarregado: **11 202 737 bytes**, SHA-256
`85888d690eecc71f062f82b6e75c243f29e2136279cb94dfa4b96d58d03c0d6d`.

Reutilizou-se `app.uk_ashe_wages.build_snapshot`, sem alterar o importador ou
executar `load_snapshot`. Os 52 registos aceites reproduzem exatamente os do Git.
Dentistas, SOC2020 2253, continuam excluídos nas duas medidas por
`suppressed_or_cv_over_20`; este motivo combinado não permite afirmar que ambas
as células sejam necessariamente suprimidas. Não reduzir o limiar nem imputar.
Um ano anterior com uma estimativa válida poderá resolver cobertura histórica,
mas ainda precisa de aquisição, ano/classificação/CV validados e suporte no leitor.

Também foi descarregada a [classificação SOC2020 oficial](https://www.ons.gov.uk/methodology/classificationsandstandards/standardoccupationalclassificationsoc/soc2020/soc2020volume1structureanddescriptionsofunitgroups),
incluindo o workbook indicado pela página, versão de ficheiro 20260827. Exemplos:

- Médicos: 2211 generalistas e 2212 especialistas; não escolher um como total.
- Enfermeiros: 2231–2237; «other registered nursing professionals» não reúne todos.
- Psicólogos: 2225 clínicos e 2226 outros.
- Auditor: 2421 inclui qualified auditors e accountants, não um salário exclusivo.
- IT technician: 3131 e 3132 distinguem operação de sistemas e apoio ao utilizador.
- Administrative assistant: aparece na classe residual 4159, com outras funções.
- Lawyer: 2412 inclui lawyers/solicitors; validar a relação com 2411/2419 e o
  âmbito EarnWage antes de admitir uma série mais estreita.

Uma leitura adicional das mesmas tabelas, reutilizando `_sheet_rows` e sem
importações, identificou candidatos concretos para revisão:

| Profissão / SOC | Valor publicado em GBP/ano | Qualidade | Impedimento restante |
| --- | --- | --- | --- |
| Agricultural worker / 9111 Farm workers | Média 27 324; mediana `x` | CV média 15%; CV mediana 23% | Restringir explicitamente a trabalho agrícola elementar; não toda a agricultura qualificada |
| Lawyer / 2412 | Mediana 53 314; média 68 462 | CV 4,6% / 4,8% | Âmbito solicitors/lawyers, não todas as profissões jurídicas |
| IT technician / 3131 | Mediana 34 656; média 38 507 | CV 4,6% / 3,7% | ASHE diz «IT operations technicians»; classificação 20260827 diz «IT technicians». Rever versão e âmbito |

O valor médio dos farm workers cumpre o controlo de CV, mas isso **não valida por
si só a correspondência profissional**. A mediana excluída continua ausente.
Valores de 4159/2421 também existem, mas respetivamente a categoria administrativa
residual e a categoria partilhada com accountants não resolvem um salário
exclusivo de administrative_assistant/auditor. Estes dados de fonte constam como
candidatos não aprovados no JSON, sem alimentar a API ou aumentar cobertura.

A página ONS descarregada declara Open Government Licence v3.0. O acesso direto
à página da licença nos National Archives falhou com ProxyError; a declaração
ONS foi lida, mas o texto completo das condições não foi novamente obtido.
Manter atribuição ONS, versão provisória e definição anual; annual/12 é um
comparador, não remuneração mensal contratual.

## Alemanha — lacunas identificadas, aquisição bloqueada

Fonte existente: [BA Entgeltatlas](https://www.arbeitsagentur.de/hilfe-entgeltatlas).
As tentativas à metodologia e a uma página profissional conhecida falharam com
ProxyError. Não se confirmou um endpoint bulk nem novas páginas KldB, regras de
supressão ou licença nesta execução. Não chamar inexistentes às 13 lacunas.

Primeira revisão recomendada: pharmacist, psychologist, receptionist,
it_technician e warehouse_operator. Cada proposta precisa da Berufsgattung
original, nível de exigência, população, ano, unidade e ausência de fallback para
Berufsgruppe. IDs de páginas não são códigos KldB. Reutilizar o módulo
`de_entgeltatlas_wages` e o registo de classificações quando houver evidência;
não introduzir códigos por semelhança de nomes.

Pré-requisito externo: acesso HTTPS a `www.arbeitsagentur.de` e
`web.arbeitsagentur.de`, ou entrega do ficheiro oficial e metodologia com URL,
versão, data e checksum. Não contornar controlos de rede nem assumir licença.

## França — fonte oficial completa, âmbito preservado

Fonte: [INSEE DS_DERA_PRIVE_ANNUEL 2024](https://api.insee.fr/melodi/file/DS_DERA_PRIVE_ANNUEL/DS_DERA_PRIVE_ANNUEL_2024_CSV_FR).
Apesar do nome do endpoint, a resposta é um **ZIP**, contendo os CSV de dados e
metadados. Os hashes do ZIP e de ambos os membros constam do relatório.

A seleção usa explicitamente `GEO=F`, `GEO_OBJECT=FRANCE`, `FREQ=A`,
`ACTIVITY=AGE=NUMBER_EMPL=SEX=WKTIME=QUANTILE=_T`, `TIME_PERIOD=2024`,
`DERA_MEASURE=SALAIRE_NET_EQTP_MENSUEL_MOYENNE`, `UNIT_MEASURE=XDC`.
Foram encontrados **366 registos de média nacional nesse âmbito**, incluindo
categorias agregadas: não são 366 profissões aprovadas. Nos 23 mappings existentes,
valor salarial e efetivo EQTP coincidem com o download, usando Decimal no confronto.

A análise das designações demonstra impedimentos concretos:

- 388A inclui engenharia, investigação e desenvolvimento informático; não é
  automaticamente um salário exclusivo de software developers.
- Contabilidade e finanças distinguem empregados, técnicos e quadros, com âmbitos
  mistos. Não publicar os mesmos grupos como accountant/auditor/financial_analyst.
- Receptionist: 541B qualificados e 541C não qualificados.
- Waiter: 561B qualificados e 561C não qualificados.
- Warehouse operator: 652A inclui manuseamento qualificado/caristas e 676A
  manuseamento não qualificado.
- Agricultura está fora do universo descrito deste dataset.

Não juntar subclasses por média simples nem usar efetivos EQTP como ponderadores
sem validar a metodologia, completude e correspondência pretendida. Esta é uma
fonte de **líquido estatístico**, não uma validação do motor fiscal nem salário bruto.

A página de catálogo/licença data.gouv.fr ficou bloqueada; uma tentativa de página
INSEE para condições devolveu 404. **Licença de redistribuição ainda por confirmar**:
não atribuir CC BY por suposição nem preparar publicação com esta lacuna.

## Países Baixos — acesso recuperado, história disponível

Fonte: [CBS 86355NED](https://datasets.cbs.nl/odata/v1/CBS/86355NED).
A primeira consulta `$metadata` devolveu 406. Repetiu-se com o formato adequado:
`Accept: application/xml` para `$metadata`; `application/json` para entidades.
Metadados, Properties, BeroepCodes, PeriodenCodes, MeasureCodes e Observations
ficaram acessíveis. Não é necessário um sistema paralelo de importação.

O download integral contém **7 465 observações**, igual ao `ObservationCount`
publicado; sem `@odata.nextLink`. São **962 681 bytes**, SHA-256
`097c2dbe156374aee00623f86570a0c5808e26a1329cff3566b7d2f30453053c`.
Versão `202608180000`, licença declarada em Properties: **CC BY 4.0**.
Atribuir CBS, dataset/versão, indicar o processamento EarnWage e preservar a licença.

Seleção privada para revisão: códigos CBS das 21 correspondências já aprovadas,
medida `A043068` (mediana), período original anual e estado oficial. Só entram
valores positivos finitos com `ValueAttribute=None`; missing não vira zero.
Resultam **265 medianas em 2013–2025**, sem marcadores missing nos registos
selecionados. Há **8 combinações profissão/ano sem observação** no produto
21 × 13; continuam ausentes, sem imputação ou zeros. As 21 células
correspondentes ao snapshot têm valores iguais; as outras **244** são candidatas
históricas relativamente ao Git. **Não são 244 valores novos em produção**.
Não se aumentam os 21 pares país/profissão.

| Anos | Observações anuais selecionadas |
| --- | ---: |
| 2013–2018 | 20 por ano |
| 2019–2024 | 21 por ano |
| 2025 | 19 |

Properties e `PeriodenCodes.Status` indicam 2013–2024 definitivos e 2025 provisório.
A descrição textual de 2024 em PeriodenCodes ainda diz «Voorlopige cijfers»:
registar esta inconsistência, preservando metadados originais e sem promover 2025
porque a descrição de outro campo esteja desatualizada. Os mappings de docentes
usados no snapshot em 2024 não passam automaticamente a 2025.

As definições oficiais excluem remunerações especiais e horas extraordinárias;
as horas remuneradas excluem horas extra e férias/feriados. Não multiplicar o
salário horário por horas anuais presumidas.

Para as 19 lacunas, há vários grupos incompatíveis: Artsen (1011) junta médicos,
veterinários, dentistas e farmacêuticos; 0712 junta várias engenharias; 1213 junta
condutores de autocarro e elétrico; 0742 inclui soldadores e trabalhadores de chapa.
Não os apresentar como novos salários individuais. Outras lacunas continuam em
revisão de classificação, não como prova de indisponibilidade estatística.

## Tarefas pequenas seguintes, por prioridade

1. **Reino Unido: rever candidatos e história dos dentistas.** Priorizar 9111 e
   2412 com âmbito explícito; resolver a revisão de 3131. Adquirir um release anterior
   oficial, validar SOC2020, tabelas 14.7a/b, ano e CV. Só depois generalizar o
   parser/leitor para histórico, com testes de não mistura de releases.
2. **Alemanha: desbloquear e rever cinco profissões.** Uma correspondência e prova
   por tarefa; começar por pharmacist/psychologist. Não modificar os 27 dados atuais.
3. **Países Baixos: adaptar história das correspondências existentes.** Reutilizar
   `nl_cbs_wages` e staging/proveniência existentes, preservar precisão BRC,
   versão, atributos de falta e estado anual. Rever as 244 candidatas e comparar
   com inventário autorizado abrangendo a tabela NL antes de escolher um pacote.
4. **França: confirmar licença e âmbito das subclasses.** Só propor mappings
   após revisão detalhada PCS-ESE. Uma série independente com âmbito explícito
   pode ser útil, mas não deve preencher uma profissão genérica indevidamente.
5. **Publicação:** adaptar a projeção controlada às tabelas Europeias, se aprovada.
   A via bulk salarial atual de BLS/Job Bank não basta para publicar estas séries.
   Exigir inventário atualizado, checksums, prevenção de conflitos, backup,
   ensaio de recuperação e aprovação específica; esta PR não implementa publicação.

## Reprodutibilidade e validação

Inventário existente, sem apontar para bases:

```sh
.venv/bin/python -m scripts.bulk_inventory --output /workspace/europe-inventory
```

O relatório completo gerado fica fora do Git; a PR guarda apenas resumo, matriz e
provas compactas. As aquisições são reais, não fixtures nem exemplos sintéticos.
Os binários/raw CSV/JSON e a seleção histórica permanecem privados; os hashes
identificam exatamente os ficheiros obtidos. Reaquisição posterior pode produzir
hash diferente se a fonte publicar uma revisão, exigindo nova comparação.

Os testes da PR confrontam o resumo com o inventário existente, hashes dos
snapshots, catálogo e cobertura sem duplicar médias/medianas, e impedem que
candidatos ou acessos bloqueados sejam descritos como publicáveis. Os leitores
nacionais são exercitados pelos testes existentes. Suite dirigida: **27 aprovados**.
Suite completa: **669 aprovados, 0 falhas e 20 subtests aprovados**, em 89,87 s;
um aviso Starlette herdado. Sete testes novos verificam consistência da auditoria.
