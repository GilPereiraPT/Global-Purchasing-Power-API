# Issue #25 — reconciliação salarial offline

## Estado: inventário actualizado pendente

Preparação em 4 de outubro de 2026 (Europe/Lisbon), a partir de main
`59aecd0875e4d6fb3d78ff07adfde06dff22f356`. Nenhuma comparação com produção
foi iniciada. Os exports anteriores não são usados como inventário actual.
Novas observações, duplicados, revisões, incompatibilidades e primeiro pacote
ficam **não determinados**, nunca zero nem implicitamente elegíveis.

## Staging confirmado

Ambas as bases privadas da Fase 4B continuam disponíveis. Os hashes foram
recalculados e coincidem exactamente com o manifesto privado criado para a
exportação de staging. Não houve download, importação ou escrita nestas bases.

| Fonte | Bytes | SHA-256 |
|---|---:|---|
| BLS OEWS | 2 462 720 000 | `6be2fe4ae98659a031460a09234d1b334ebd47d63d0b104948fdb025f1ecc069` |
| Job Bank | 51 671 040 | `c48c29339823aa74b76fc2193b8126fc69207b3b53aa8b4dbcb45cdd03611a04` |

As contagens de referência do manifesto e da Fase 4B são 868 201 observações
aceites BLS e 14 018 Job Bank; 13 565 versões BLS em quarentena e valores em
falta não são candidatos. Contagens de staging não demonstram novidade em
produção. As bases, arquivos e inventários privados não entram no Git.

## Entrada necessária e procedimento existente

O operador deve fornecer **novo ZIP do botão «Exportar inventário salarial» do
Data Manager**, o SHA-256 do ZIP e a autorização de utilização apenas para
reconciliação offline na Issue #25. Não são necessários token, configuração ou
SQLite produtivo. Seguir [PHASE4F.md](PHASE4F.md) e
[PHASE4E.md](PHASE4E.md), secções A/B.

Depois de receber a entrada: validar manifest/schema/hashes/completude das três
tabelas, normalizar as identidades reconstruíveis e marcar âmbitos ambíguos ou
parciais. Reutilizar `app/bulk_inventory_export.py`,
`scripts/bulk_compare_inventory.py` e `scripts/bulk_inventory.py`; leitura
SQLite `mode=ro`, sem importer nem inicialização de bases produtivas.

Considerar BLS em `us_oews` **e** `north_america_wages`; preservar fonte, SOC2018,
NOC2021, aliases, geografia, período original, indústria/ownership, medida,
unidade/moeda e restantes dimensões. Não dividir 2023–2024 em dois anos e não
contar accountant/auditor como duas observações físicas BLS. Comparar ambas as
bases com o mesmo export autorizado; separar novas, duplicadas, revisões,
quarentena, NULL, incompatibilidades e linhas protegidas.

Seleccionar pacote só após evidência completa: uma linha nacional histórica com
mapping aprovado, período mais antigo elegível e todas as medidas juntas; preview
local do modelo autorizado e protecção de valores existentes. O antigo candidato
software_developer/May 2021 foi comunicado como publicado: não o seleccionar
novamente sem confronto com o export actualizado. Preparação de pacote não
constitui autorização de publicação.

## Verificação preliminar

Foram executados os testes existentes dos comparadores/exportador e projecção
salarial: `tests/test_bulk_inventory_export.py`,
`tests/test_operator_salary_inventory.py`, `tests/test_bulk_publication.py`.
Resultado indicado na PR. Fixtures locais não constituem uma comparação com
produção. Não se alteraram código, contratos, salários, fiscalidade, câmbios,
Android, deployment ou agendas. A PR fica em draft enquanto faltar o inventário.

Resultado local: 55 passed in 0.61s
