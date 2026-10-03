# Job Bank — salários nacionais e regionais

O adaptador `app.bulk_job_bank` utiliza o Downloader/ledger/worker da Fase 4 e o
novo leitor estrito `bulk_rows` no módulo provincial existente. A função `records`
anterior e os endpoints nacionais/provinciais conservam os contratos existentes.

## Validação oficial, 3 de outubro de 2026

- Catálogo CKAN: https://open.canada.ca/data/api/action/package_show?id=adad580f-76b0-4502-bd05-20c125de9116
- Dataset: https://open.canada.ca/data/dataset/adad580f-76b0-4502-bd05-20c125de9116
- Recurso CSV: `9da94d63-b178-4a64-aeb3-b6a3bd721ad2`, ficheiro
  `2a71-das-wage2025opendata-esdc-all-19nov2025-vf.csv`.
- Destino observado: `opencanada.blob.core.windows.net`, prefixo público
  `/opengovprod/resources/`. Redireccionamentos para hosts/prefixos não registados
  são rejeitados; HTTPS mantém verificação de certificados.
- Licença confirmada no catálogo: Open Government Licence — Canada,
  https://open.canada.ca/en/open-government-licence-canada (`ca-ogl-lgo`).
- Metadados modificados em `2025-11-19T15:21:45.787073`.
- CSV completo: **44 376 linhas**, 516 códigos NOC2021 e 86 identificadores
  geográficos: nacional, 13 totais provinciais/territoriais e 72 outras regiões
  económicas. Os totais de províncias territorialmente coextensivas com regiões
  económicas continuam classificados como totais provinciais, sem duplicação.

Os nomes e códigos publicados estão no pequeno registo
`data/job_bank_2025_geographies.json`, extraído do CSV oficial completo e usado
para validar cada par código/província/nome. Não é um novo universo geográfico
inventado nem um mapeamento de cidades. Alterações de nomes/códigos/layout/licença
exigem revisão e falham de forma explícita. NOC2021 é a classificação do recurso
revisto, confirmada pela documentação/códigos/títulos do catálogo existente.

As seis medidas originais (low, median, high, mean, p25, p75) são separadas. O flag
original define CAD/hour ou CAD/year; o import não converte unidades nem inventa
médias. Campos vazios conservam `null`. `Reference_Period=NA` só é admitido quando
não há nenhum salário; fica `period=unknown`, com `original_period=NA`. Não é
atribuído a 2025. `2023-2024` permanece um único período, nunca duas observações.
São preservados a fonte estatística original, data de revisão e origem/licença.

Todas as linhas passam pela validação; somente os códigos já aprovados para as
38 profissões EarnWage são seleccionados. Códigos partilhados por profissões do
catálogo não duplicam observações físicas. Não há substituição de nacional por
provincial/regional e não se infere ausência nacional a partir de regiões.

## Execução

```bash
.venv/bin/python -m scripts.bulk_acquire --workspace /caminho/privado/job-bank \
  --provider job_bank --dataset 2025
```

Nesta entrega houve **aquisição live completa**, não apenas testes de amostras.
Resultado: 14 018 observações aceites, zero em quarentena e 5 074 células em falta
preservadas; 3 182 linhas seleccionadas, 41 194 fora dos códigos alvo. A repetição
revalidou as 44 376 linhas e retomou 19 092 observações sem novas inserções.

Os testes usam quatro linhas autênticas extraídas do CSV completo, identificadas
em `tests/fixtures/bulk/salary_provenance.json`; valores de campos preservados,
quoting normalizado. Esses testes não são contados como aquisição live. O CSV
completo e os dashboards gerados não são adicionados ao Git.

O acesso do ambiente cloud foi alargado apenas ao host público de destino,
preservando os domínios anteriormente autorizados. Em instalações futuras,
autorizar `open.canada.ca` e `opencanada.blob.core.windows.net` para esta aquisição.
Não modificar segredos produtivos. URLs SAS transitórias são usadas apenas no
pedido HTTPS; a query é retirada dos metadados persistidos e não aparece em logs
ou na documentação. O worker reporta apenas o tipo de erro.
