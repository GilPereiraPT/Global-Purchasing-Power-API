# Histórico salarial CBS — preparação isolada

Branch independente a partir da main `d2e0fdb`, posterior à investigação PR #34.
Não há downloads adicionais, publicação, alteração dos salários existentes,
fiscalidade, câmbios, Android, deployment ou ativação de schedules.

## Implementação

`app.nl_cbs_wages` passa a reproduzir uma seleção histórica a partir dos cinco
ficheiros oficiais completos já recolhidos: Properties, BeroepCodes, PeriodenCodes,
MeasureCodes e Observations. Reutiliza os 21 mappings aprovados e o schema de
20 colunas da tabela `nl_cbs_wages`; não acrescenta profissões por semelhança.

A versão revista é **CBS 86355NED / 202608180000**, classificação **BRC 2014 editie
2025**, incluindo as séries históricas publicadas pelo CBS nessa edição. Não se
assume que cada ano usava originalmente a mesma edição da classificação.
Licença declarada em Properties: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Atribuição: CBS, dataset 86355NED, versão 202608180000; seleção/processamento EarnWage.

A validação exige hashes independentes fixados no código para os cinco ficheiros,
release/licença/classificação, universo anual, medidas/unidades, contagem integral,
IDs e dimensões únicos e ausência de paginação incompleta. Rejeita dimensões
inesperadas, campos duplicados, NaN, valores booleanos, symlinks, ficheiros ausentes
ou superiores a 5 MiB. Um ficheiro com hash diferente exige nova revisão; não
atualizar os hashes só para contornar uma falha.

O review derivado tem dois hashes canónicos igualmente fixados: registos e
metadados/proveniência/completude. Um caller não autentica alterações recalculando
um checksum fornecido por si. As datas registadas são preservadas: início dos
pedidos de metadados e conclusão do download de Observations, explicitamente
identificados; não se inferem datas do mtime dos ficheiros.

`stage_history_review` reutiliza **BulkStore**, com registo de artefactos, versões,
checkpoints, limiar de revisão, quarentena e estado das execuções. O novo comando
offline reutiliza `safe_workspace` e `exclusive_worker`; exige pasta explícita
fora do Git, evita pastas/configuração de bases da aplicação, preserva ficheiros
temporários preexistentes e produz relatórios por substituição atómica.
Não há outro painel, importador de produção ou conector de rede paralelo.

## Resultado real, não contagens de fixtures

| Resultado | Quantidade |
| --- | ---: |
| Observações no download CBS completo | 7 465 |
| Medianas selecionadas, 2013–2025 | 265 |
| Combinações profissão/ano sem observação | 8 |
| Aceites pelo BulkStore isolado | 264 |
| Em quarentena | 1 |
| Sobreposições iguais ao snapshot atual | 21 |
| Históricos aceites adicionais face ao Git | 243 |
| Novas profissões | 0 |

A quarentena é **warehouse_operator / 2023**, EUR 11,7/hora, depois de EUR 8,8
em 2022: aumento de aproximadamente **32,95%**, superior ao limiar genérico de 30%.
A fonte publica o valor, mas ele continua pendente de revisão da variação e
comparabilidade; não se alterou o limiar nem se aprovou a observação para aumentar
cobertura. 2024 e 2025 permanecem registos independentes segundo a validação
existente; não são usados para aprovar silenciosamente 2023.

As 244 candidatas históricas iniciais tornam-se 243 aceites e uma quarentena.
Estas são diferenças **face ao snapshot do Git**, não novidades confirmadas na
produção. O inventário autorizado US/CA da Issue #25 não cobre a tabela NL.
Não foi efetuada qualquer comparação com produção nesta tarefa.

As oito combinações ausentes não geram salários zero nem observações fictícias.
Marcadores missing/supressão ficam em exclusões com o original e `value=null`.
Preservam-se mediana, salário horário, contagem de empregados, códigos CBS,
período original `YYYYJJ00`, IDs das observações, atributos e estado do período.
Não se transformam percentis/contagens em médias salariais.

## API e compatibilidade

**O snapshot atual de 21 registos não foi alterado.** Startup ASGI/WSGI continua
com o mesmo carregamento. Nenhuma configuração ativa o histórico automaticamente.
O reader existente aceita anos históricos presentes na tabela compatível; o
comando offline escreve apenas `staging.sqlite3` e reviews, nunca nessa tabela.

O histórico NL preserva agora `publication_status` e período nos
`source_observations`. Corrige a identificação de precisão para
`approved_direct_brc_occupational_group`, no histórico e no salário horário,
sem alterar os campos monetários, estrutura de endpoints ou outras fontes.
Essa identificação não promete salário exclusivo de uma profissão universal.
A nota de um salário definitivo usa o seu ano, em vez de dizer sempre «2024».

2013–2024 são definitivos; 2025 é provisório. O campo Description de 2024 ainda
contém «Voorlopige cijfers»: preservado na proveniência, sem substituir o Status
oficial e Properties que identificam 2024 como definitivo.

Salário bruto horário exclui pagamentos especiais e remuneração de horas extra;
as horas remuneradas excluem horas extra e férias/feriados. Não se presumem
horas anuais, pagamentos mensais nem líquido; annual_presentation continua
indisponível para estas observações horárias.

## Reproduzir sem rede ou produção

Disponibilizar os cinco ficheiros originais em pasta privada, com estes nomes:

- `NL-properties.body`
- `NL-occupation_codes.body`
- `NL-period_codes.body`
- `NL-measure_codes.body`
- `NL-observations.body`

URLs e hashes individuais constam do código e da evidência agregada. Não enviar
bases de produção, credenciais ou configuração. Executar no checkout da branch:

```sh
.venv/bin/python -m scripts.nl_cbs_history \
  --source-directory /workspace/fontes-cbs-validadas \
  --workspace /workspace/earnwage-nl-cbs-history \
  --acquired-at 2026-10-04T13:43:35.954865+00:00
```

Saídas privadas: staging SQLite, `cbs-history-review.json` e
`cbs-history-result.json`. A primeira execução aceita 264 e deixa uma quarentena;
a segunda retoma 265 linhas sem inserções. Os contadores da última invocação são
incrementais; consultar `staging.accepted_observations` e `quarantined_versions`
para os totais persistentes, mesmo quando a segunda invocação reporta zero.
A pasta retém ficheiros para auditoria/reconciliação e pode ser removida
manualmente depois de concluído o trabalho; nunca inclui bases ativas.

O JSON de review **não é um pacote Data Manager**. `bulk_publication.projection`
continua a rejeitar CBS. Esta PR não acrescenta suporte de publicação nem altera
os respetivos gates de autenticação, ativação, backup ou recuperação.

## Ensaios e passos necessários antes da publicação

Uma simulação exclusivamente local, usando os aceites do staging, confirmou:
21 linhas anteriores preservadas; 243 inserções compatíveis; 21 duplicados;
repetição com zero inserções; quarentena 2023 excluída; integridade SQLite `ok`.
Essa simulação é prova de compatibilidade do modelo, **não um mecanismo autorizado
para escrever em produção**. Não usar INSERT OR IGNORE como substituto da futura
comparação/autorização Data Manager.

O arquivo real do workflow de deployment foi gerado/instalado numa pasta isolada.
O WSGI serviu histórico horário com estados anuais, mantendo o salário mais
recente e sem importar FastAPI. Regras existentes incluem scripts, mas não os
executam; raw files, reviews, staging, fixtures e docs não entram no archive.
Nenhuma regra de deployment foi alterada.

Fixtures pequenas contêm oito pares reais mediana/empregados; ObservationCount
é ajustado ao subset exclusivamente nos testes. Os testes substituem hashes
confiáveis só no processo isolado. Nunca tratar estas amostras como releases
completos ou como nova aquisição live. As contagens 264/1 provêm dos ficheiros
oficiais completos verificados, não das fixtures.

Antes de publicar: obter um inventário autorizado que abranja `nl_cbs_wages`,
reconciliar período/fonte/medida/classificação/população, resolver a quarentena
apenas com evidência, adaptar a projeção controlada existente para CBS numa tarefa
própria, e repetir backup/ensaio de recuperação/limites/autorização de checksum.
Não existe nesta entrega um pacote autorizado nem publicação automática.

[Evidência compacta](nl-cbs-history-evidence.json) inclui hashes, contagens,
simulação local e resultados dos testes. Dados completos e bases ficam fora do Git.

Validação: **697 testes aprovados, 0 falhas e 20 subtests aprovados**;
39 testes direcionados aprovados, incluindo o archive WSGI. Um aviso Starlette
herdado. O GitHub Actions é registado na PR quando concluído.
