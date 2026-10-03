# BLS OEWS — bulk salarial

O adaptador `app.bulk_bls` reutiliza `app.us_oews.workbook_records` e a validação de
ZIP existente. O argumento `bulk=True` activa validação estrita e retenção de
salários totalmente suprimidos; a chamada anterior conserva o contrato original.
Usa exclusivamente Downloader, cache, ledger e worker da Fase 4.

Fontes oficiais:

- Releases: https://www.bls.gov/oes/tables.htm
- Classificação: https://www.bls.gov/oes/oes_ques.htm
- Metodologia: https://www.bls.gov/opub/hom/oews/concepts.htm
- Release 2025: https://www.bls.gov/oes/special-requests/oesm25all.zip

A FAQ e o Handbook confirmam que maio de 2021 foi a primeira edição baseada
inteiramente em SOC 2018. Releases 2021–2025 são registados, com códigos originais
`SOC2018:xx-xxxx`. O catálogo também disponibiliza 2014–2020 em XLSX e 2011–2013
em XLS, além de ficheiros mais antigos separados. Essas edições ficam **indisponíveis
neste adaptador**: SOC 2010/transição híbrida e layouts XLS exigem validação própria.
Não se aplica retrospectivamente a classificação actual. Novas edições exigem
validação e registo explícito, não descoberta seguida de importação automática.

Todos os registos do workbook completo são lidos e validados. A selecção admitida
é: códigos SOC detalhados previamente aprovados para EarnWage, `NAICS=000000`
(cross-industry), `OWN_CODE=1235` (all ownerships). Outras profissões, grupos,
indústrias e âmbitos de propriedade não expandem cobertura individual. Os contadores
`source_rows`, `selected_rows` e `excluded_rows` tornam esta selecção auditável.
Um código partilhado por accountant/auditor conta como uma observação física e duas
referências do catálogo, não dois salários independentes.

O próprio workbook define `AREA_TYPE`: 1 nacional, 2 estado, 3 território dos EUA,
4 MSA, 6 área não metropolitana. FIPS/MSA/códigos específicos BLS, nomes originais,
SOC, unidade horária/anual e medidas mean/median/p10/p25/p75/p90 são preservados.
Não se infere uma cidade nem se substitui nacional por regional. Não se anualizam
salários horários. `*`, `**`, `#` e outros tokens reconhecidos ficam `value=null`
no ledger, com o token original; valores arbitrários não numéricos fazem falhar a
validação. O período original `May YYYY` permanece ao lado do ano de observação.

```bash
.venv/bin/python -m scripts.bulk_acquire --workspace /caminho/privado/bls \
  --provider bls --dataset 2021 --dataset 2022 --dataset 2023 --dataset 2024
.venv/bin/python -m scripts.bulk_acquire --workspace /caminho/privado/bls \
  --provider bls --dataset 2025
```

Limites: quatro datasets por invocação, 96 MiB por download, 1,5 GB de expansão
ZIP/XLSX, um milhão de linhas, HTTPS verificado, cache SHA-256, batching de 1 000
observações. A comparação temporal usa um índice de série com todas as dimensões,
evitando varrer todo o país/indicador para cada salário. A migração é apenas no
ledger de staging; não toca no esquema produtivo. Uma dimensão extra participa na
identidade e impede misturar indústria/propriedade/população.

Variações suspeitas mantêm a quarentena da Fase 4. Uma execução interrompida pode
ter lotes anteriores no staging, mas permanece `failed`; o dashboard exclui os dados
da última execução incompleta e a exportação existente impede promoção. Este
conector não instala salários na API produtiva nem altera os seus contratos.
