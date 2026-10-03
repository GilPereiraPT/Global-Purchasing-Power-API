# Inventário de produção autorizado

Para o operador: seguir o [guia Phase 4E](PHASE4E.md). O dashboard público e
`/v1/data-inventory` são agregados e **não** fornecem este protocolo observacional.
O botão «Exportar inventário salarial» do Data Manager ([Phase 4F](PHASE4F.md))
exporta as três tabelas salariais em leitura, sem inicializar a aplicação.
A alternativa CLI usa a mesma implementação partilhada. Essa exportação bruta preserva as identidades do modelo
existente; será normalizada offline e revista antes de usar os comandos abaixo.
Não confundir o seu `manifest.json` com um inventário observacional já normalizado.

Não é feita qualquer ligação à produção. O operador fornece um ficheiro JSON local,
exportado com autorização, sem credenciais ou dados pessoais. Um inventário agregado
não permite distinguir observações novas, revisões e duplicados.

Formato mínimo:

```json
{"schema":"earnwage-observation-inventory-v1","scope":"complete","exported_at":"2026-10-03T00:00:00Z","observations":[{"provider":"bls","dataset":"OEWS","country":"US","geography":"national","indicator":"occupational_salary","classification":"SOC2018:15-1252","measure":"mean","unit":"USD/year","currency":"USD","period":"2025","dimensions":{"industry":"000000","ownership":"1235","occupation_group":"detailed"},"value":"100000"}]}
```

Os identificadores têm de usar a mesma normalização do staging; a exportação deve
incluir as dimensões originais relevantes (indústria, propriedade, população, etc.).
`classification` e `currency` podem ser `null` para indicadores económicos. Valores
publicados em falta usam `null`. Alias de profissões não são observações adicionais.
Os campos por observação são exclusivamente os identificadores do exemplo,
`value` e `dimensions` opcional. Nomes geográficos, URLs de aquisição e outros
metadados não são admitidos neste protocolo mínimo; dimensões relevantes adicionais
pertencem a `dimensions`, evitando que sejam descartadas silenciosamente.

```bash
.venv/bin/python -m scripts.bulk_compare_inventory \
  --staging /caminho/privado/staging.sqlite3 \
  --inventory /caminho/exportacao-autorizada.json \
  --authorization referencia-da-autorizacao-do-operador
```

A leitura do SQLite usa `mode=ro`; não se consultam variáveis de ambiente de
produção, endpoints remotos ou ficheiros de bases produtivas. A referência de
autorização regista a intenção do operador; não substitui autorização do proprietário.
Exportações parciais são identificadas como tal: «new» significa ausente da parcela
exportada, não necessariamente novo em toda a produção. Comparação numérica exacta
com Decimal, sem tolerância ou conversão de unidades. Sem exportação, a cobertura
real de produção e as diferenças ficam indisponíveis, nunca iguais a zero.

# Artefactos reproduzíveis

Os inventários e dashboards completos são gerados fora do diff da PR:

```bash
.venv/bin/python -m scripts.bulk_inventory --output docs/bulk/generated/baseline
.venv/bin/python -m scripts.bulk_inventory \
  --insights-db /workspace/phase4-final/api-offline.sqlite3 \
  --acquisition-report /workspace/phase4-final/acquisition.json \
  --output docs/bulk/generated/phase4
.venv/bin/python -m scripts.bulk_quarantine_audit \
  --staging /workspace/phase4-final/staging.sqlite3 \
  --output docs/bulk/quarantine-review.csv
```

Os caminhos `/workspace/phase4-final` identificam exclusivamente os artefactos locais
de aquisição desta revisão; noutra máquina, repetir a aquisição com o worker e usar
os respectivos caminhos. Ficheiros gerados e datasets bulk não devem ser adicionados
à PR. A evidência compacta e hashes em `acquisition-evidence.json` são preservados.

# Revisão da quarentena da Fase 4

Todas as 257 versões estão classificadas em `quarantine-review.csv`: 250 variações
numéricas e sete flags Eurostat `b` (quebra de série). O CSV conserva valor, período,
fonte, hash, motivo e comparação temporal. Os valores adjacentes são contexto de
revisão, não validação independente. Não houve aprovação automática.

Triagem adicional: 124 casos de mortalidade/conflitos, 36 de unidades monetárias
ou câmbio, 27 de direcção/escala da inflação, 63 de definições/inquéritos/séries e
sete quebras de metodologia. Estas categorias indicam o trabalho de revisão, não
identificam automaticamente a causa real da variação.

Todas requerem avaliação manual antes da promoção: confirmar revisão/metodologia,
volatilidade real ou erro de unidade/dado. Em particular, a sequência portuguesa
Eurostat de remuneração líquida inclui uma quebra e variação de ordem de grandeza;
não corrigir nem interpolar automaticamente. Variações em mortalidade/conflitos e
inflação podem ser reais, mas o valor numérico só por si não justifica promoção.
