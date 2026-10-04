# Texas e Florida — segundo pacote oficial, 2026

Revisão offline de 4 de outubro de 2026. `LEIA_PRIMEIRO_CODEX.md` foi lido como guia documental; as decisões assentam nos corpos originais, não no resumo. ZIP: 216 531 bytes; SHA-256 `9e9ae29bc87415b8c1b3cfc1893dc2c89b30d8a6d2eba10bcdb6c9dc4f764f04`. CRC, caminhos, nove tamanhos e nove hashes verificados. Os originais permanecem privados, fora de Git. Não se afirma uma nova aquisição online ou autenticação independente do servidor. Manifesto auditado: [JSON](us_local_paid_leave_uploaded_review_20261004.json), com URLs, datas, bytes e decisões individuais.

## Decisões por original

| Original | Resultado e limite |
|---|---|
| TX Insurance Code 1255 | Regula seguro privado de licença familiar emitido através de benefícios do empregador; não cria por si contribuição pública universal. |
| TDI B-0012-23 | Normas do produto HB1996, eficácia setembro de 2023/aplicação janeiro de 2024; não é inventário completo dos programas públicos de 2026. |
| FL §624.6086 | Seguro pode ser emitido/comprado pelo empregador; autorização de produto privado. |
| FL §627.445 | Termos de apólice e benefícios; duas semanas são benefício mínimo, não taxa de contribuição salarial. |
| Florida Revenue FAQ 1466 | Confirma ausência de imposto pessoal estadual; não resolve toda a incidência municipal/condado. |
| HB1217 enrolled PDF | O PDF original foi convertido independentemente: alteração ambiental, secção 5 fixa 1 de julho de 2026. Não é tabela salarial nem texto promulgado descarregado. |
| HB1217 histórico oficial | Liga a versão enrolled; aprovação pelo governador em 22 de abril, capítulo 2026-45 em 23 de abril e eficácia em 1 de julho. Fecha o pedido específico da data/matéria. |
| Texas payroll state/local | Orientação para empregados do estado que vivem/trabalham fora do Texas; não prova zero local do empregado privado residente. |
| Texas STAR 9610803L | Rejeitado: HTML da aplicação sem corpo da carta. Fragmento de pesquisa sobre 1996 não valida regra em 2026. |

O manifesto também regista duas consultas sem corpo (403: diploma promulgado 2026-45 e TWC work-family). Não são originais validados. O enrolled refere §377.816, enquanto §166.201 anteriormente fornecido refere §377.8161: não se presume igualdade de versões/renumeração. A combinação enrolled/histórico fundamenta apenas data e matéria ambiental, sem derivar zero salarial ou pedir novamente esses documentos.

## Cobertura final

| Componente | TX | FL |
|---|---|---|
| Federal, AMT e FICA | Modelo condicionado existente | Modelo condicionado existente |
| Imposto estadual salarial | Zero com fundamento limitado já revisto | Zero já revisto, FAQ corrobora |
| UI/reemployment | Zero no cenário privado ordinário | Zero no âmbito previamente revisto |
| Workers’ compensation | Zero condicionado; preservar exceções legais | Zero condicionado; preservar exceções legais |
| Seguro privado de licença familiar | Regras do produto revistas; prémio não calculado | Regras do produto revistas; prémio não calculado |
| Imposto local | Cobertura não validada | Cobertura não validada |
| Contribuição pública paid leave/disability | Aplicabilidade não validada | Aplicabilidade não validada |
| Resultado líquido | `partial`, `net_income=null` | `partial`, `net_income=null` |

A API acrescenta metadados sobre seguros privados e fontes, mantendo contratos existentes e equivalência ASGI/WSGI. Não calcula nova taxa nem afirma custo zero de prémios. O benchmark é anterior a prémios de benefícios privados; isso não torna facultativos descontos exigidos por um contrato individual. Falta de evidência não estabelece uma obrigação pública nem prova que não existe. Fontes limitadas continuam `parameters_reviewed`, não autorização de líquido completo.

## Prova adicional mínima

Apenas quatro conclusões oficiais continuam necessárias: incidência/não incidência salarial local de TX (Comptroller/Legislature), de FL (Department of Revenue), e existência/ausência de contribuição pública de licença/disability do empregado privado em 2026 em TX (TWC/DOL) e FL (FloridaCommerce/DOL). O [pedido detalhado](US_TX_FL_SOURCE_REQUEST_2026.md) indica âmbito, URLs e alternativas. Não repetir documentos de seguros privados ou o pedido da data ambiental já fornecidos. Uma resposta oficial completa para cada âmbito basta; se depender de localidade/programa, indicar exatamente quais.

Antes de líquido futuro também são necessários factos explícitos de residência/trabalho exclusivamente no estado e casos completos de referência independentes. Não há alterações à BD, salários, deployment ou Android; nenhuma ativação, publicação ou merge.

## Validação

107 testes específicos aprovados, zero falhados: classificação de seguros, prova incompleta, não criação de contribuição presumida, exceções, paridade e arquivo WSGI real isolado. Resultado da suite completa registado após conclusão abaixo.

Validação desta revisão: **1009 testes aprovados, zero falhados, 20 subtestes aprovados**, 91,76 s; 107 testes específicos aprovados. Arquivo WSGI de deployment testado exclusivamente em instalação isolada. Um aviso herdado Starlette/httpx permanece. `git diff --check` aprovado. CI deve ser confirmado no SHA final.
