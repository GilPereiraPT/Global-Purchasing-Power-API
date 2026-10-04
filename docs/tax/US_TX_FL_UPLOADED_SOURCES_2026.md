# Validação do ZIP oficial e componentes contributivas TX/FL — 2026

Revisão: 4 de outubro de 2026. ZIP recebido: 334521 bytes, SHA-256 `d5cae18e8651806f65f371662dc78d84f58670d88c5ad14806381ebbd79586c2`. CRC ZIP, paths, limites de extração, tamanho e SHA-256 de **todos os dez corpos originais** coincidem com o manifesto. Não há checksum de ZIP fornecido independentemente pelo operador: o valor acima foi calculado nesta tarefa. Não se confunde consistência do arquivo com autenticação independente da origem ou completude jurídica.

`LEIA_PRIMEIRO_CODEX.md` foi lido como orientação do anexo, sem substituir a instrução do utilizador ou a análise dos corpos. As regras e exceções foram confrontadas com o HTML original. TXT e texto derivado não foram usados como corpos de origem. Os originais e o ZIP permanecem privados fora do repositório; apenas evidência compacta foi acrescentada.

A matriz de todos os corpos, os hashes e decisões estão em `us_tx_fl_uploaded_review_20261004.json`. Quatro corpos sustentam novos parâmetros contributivos; dois são páginas iniciais HTML rejeitadas como PDFs legislativos; quatro servem à investigação/correção, sem autorizar zeros locais/paid leave.

## Regras contributivas incorporadas

| Estado / parcela | Evidência original e âmbito | Resultado |
|---|---|---|
| TX unemployment | Labor Code §§204.002 e 204.003, https://tcss.legis.texas.gov/resources/LA/htm/LA.204.htm. Contribuição patronal e proibição de deduzir qualquer parte no salário; texto com vigência desde 1993. | `employee_unemployment_contribution="0.00"` no âmbito privado ordinário explicitamente selecionado. Não é taxa patronal zero. |
| TX workers’ compensation | §415.006, https://tcss.legis.texas.gov/resources/LA/htm/LA.415.htm: proíbe cobrar ao empregado prémio/fee patronal, **except as provided by Sections 406.123 and 406.144**. Versão da disposição com alteração de 2005. | Zero somente no âmbito privado ordinário e com exclusão explícita de acordo excecional. Não generalizar. |
| TX exceções | https://tcss.legis.texas.gov/resources/LA/htm/LA.406.htm, §§406.123 e 406.144. Acordos entre general/hiring contractor e subcontractor/independent contractor, ou motor carrier e owner operator, admitem dedução de prémios/custos do preço contratual; vínculo de empregador é específico de workers’ compensation. A segunda disposição inclui alterações de 2017. | Categorias/acordos excluídos; não converter artificialmente contratantes em empregados ordinários. Não interpretar dedução no preço contratual como desconto universal no recibo salarial. |
| FL workers’ compensation | https://www.flsenate.gov/Laws/Statutes/2026/440.21, §440.21(1). É inválido acordo do empregado para pagar parte de prémios patronais ou financiar fundo/departamento para compensação/serviços médicos exigidos pelo capítulo. | Zero no cenário privado ordinário revisto; não estender a outros seguros/benefícios privados nem a contratantes fora do âmbito empregado. |
| FL reemployment | Evidência anteriormente revista de https://www.flsenate.gov/Laws/Statutes/2026/443.041. O ZIP atual não inclui este corpo e o seu hash não foi recalculado nesta tarefa. | Mantém-se o zero específico existente; não se afirma nova aquisição/validação do original nesta tarefa. |

Os novos registos em `data/us_tax_2026_source_evidence.json` preservam URLs originais/finais, tamanho, SHA-256, data de obtenção, proveniência do ZIP, ano de aplicação e âmbito/exceções. Permanecem `parameters_reviewed`, sem promoção a prova de modelo completo. O facto de haver alterações de 2025 noutras disposições do capítulo não altera o texto das regras citadas; nenhuma regra de vigência futura foi importada como parâmetro anual.

## API e exceções

Novos factos opcionais estritos, acrescentados ao contrato existente de `us_facts`:

```json
{
  "employment_type": "ordinary_private_employee",
  "workers_compensation_exception_agreement": false
}
```

Este fragmento não substitui os factos federais obrigatórios. `employment_type` aceita também categorias explicitamente excluídas (`independent_contractor`, `subcontractor`, `owner_operator`, `public_employee`, `special_regime`) para devolver parcial sem valores modelados, não para ativar líquido. Tipos/valores não reconhecidos dão erro de validação; o sinalizador de acordo tem de ser booleano, nunca a string `"false"`.

Sem categoria privada explícita, não há novos zeros contributivos condicionais. Sem declaração falsa explícita de acordo excecional, workers’ compensation permanece desconhecido. Sem factos federais suficientes, os montantes modelados são retidos, mesmo havendo regra legal parametrizada. A agregação `mandatory_state_employee_contributions` continua `null`, porque UI e workers’ compensation não demonstram a totalidade das obrigações.

Os componentes assumem incidência da lei do estado selecionado; a confirmação de residência/trabalho exclusivamente nesse estado ainda falta ao contrato para um líquido completo. Os pressupostos e os factos necessários são expostos na API. Chamadas anteriores sem os novos factos continuam parciais; não alterámos endpoints, salários, fiscalidade PT, Android, deployment ou BD.

## Correção local e paid leave

A referência anterior a Texas Tax Code capítulo 302 como proibição de imposto municipal sobre rendimento era incorreta. O original trata de property taxes e occupation taxes (§§302.001 e 302.101); foi retirado como fundamento de imposto salarial zero. Não há regra desse capítulo no runtime. A sua história de vigência desde 1987 não valida uma proibição que o texto não contém.

Florida §166.201 autoriza tributação/licenças dentro da constituição/lei geral e fees por ordinance; menciona o capítulo **2026-45** e §377.8161. Falta o diploma completo e a data de eficácia para verificar a mudança durante 2026. A Constituição, artigo VII §1(a), exige autorização legal para os tributos locais; §5(a) contém limite ligado a montantes creditáveis/dedutíveis, não uma proibição incondicional. Não se infere zero local destes excertos.

A página DOL paid leave tem interativos e uma secção paid sick leave com data de **dezembro de 2024**. Essa data não foi apresentada como data de todos os programas de paid family/medical leave; o corpo estático não contém prova completa/temporal de ausência de contribuições TX/FL em 2026. Paid sick leave devido pelo empregador é distinto de seguro público de licença financiado pelo empregado. `employee_paid_leave_contribution` é agora uma componente explicitamente desconhecida.

As novas consultas dos localizadores Texas Local Government Code 101, Laws of Florida 2026-45, TWC e Florida §627.445 foram bloqueadas. Os localizadores não lidos não são fontes de regras incorporadas. O [pedido atualizado](US_TX_FL_SOURCE_REQUEST_2026.md) especifica o que ainda fornecer; não pede novamente os capítulos recebidos.

## Conteúdo rejeitado

`tx_labor_code.html` e `tx_tax_code.html` têm o mesmo hash `dbfba8a96dc3cd584157ca66aaafdf67e0ed15dd5a0c8a58f3d4bd0f109fc646`. São páginas iniciais HTML recebidas em URLs terminados em `.pdf`. Mesmo HTTP 200 e hashes corretos não os tornam os PDFs pedidos. Não foram incorporados como legislação ou parâmetros. O texto `tx_tax_code.txt` também não substitui o original legislativo.

## Cobertura final desta etapa

| Parcela / âmbito comprovado | TX | FL |
|---|---|---|
| Federal: imposto regular, AMT, Social Security, Medicare e Additional Medicare | modelo anual condicionado 2026, com factos/range explícitos; não liquidação final | igual |
| Imposto estadual sobre salário ordinário | zero específico anteriormente revisto, Constituição VIII §24-a | zero específico anteriormente revisto, §220.02 |
| Contribuição do empregado unemployment/reemployment | **0.00** com `employment_type=ordinary_private_employee`, §§204.002/204.003; factos federais válidos | **0.00** no cenário federal válido, §443.041; evidência anterior |
| Workers’ compensation do empregado | **0.00** com emprego privado ordinário e `workers_compensation_exception_agreement=false`, §415.006; §§406.123/406.144 excluídos | **0.00** com as mesmas declarações restritivas, §440.21(1) |
| Imposto local | cobertura não validada; **não há imposto/dívida local presumida** | cobertura não validada; **não há imposto/dívida local presumida** |
| Paid leave/disability | cobertura temporal/financiamento 2026 não validado; **nenhuma contribuição obrigatória estabelecida pela evidência** | igual |
| Agregado das contribuições obrigatórias | `null`: UI/WC não comprovam completude; não é soma de obrigações presumidas | igual |
| Líquido total | **`partial`, `net_income=null`** | **`partial`, `net_income=null`** |

Zeros são parcelas jurídicas específicas dentro do cenário, não prova de todos os descontos ou de salário efetivamente pago. Factos ausentes/categorias excluídas não autorizam os zeros condicionados. O [pedido de fontes](US_TX_FL_SOURCE_REQUEST_2026.md) identifica quatro regras, organismos e documentos necessários, sem presumir contribuição nem repetir as aquisições concluídas.

As referências contributivas independentes seguem o texto legal (zero por proibição de chargeback, não por algoritmo de taxa): casos no intervalo 19540–500000, incluindo teto Social Security e limite Additional Medicare, com contraexemplos de contratantes/acordos/factos ausentes. Não são referências de líquido completo e não permitem anunciar a fiscalidade TX/FL concluída. Testam também tipos inválidos, metadados, ASGI/WSGI e o arquivo WSGI real em instalação isolada, com e sem os novos factos. A execução completa está registada abaixo; não é necessário repetir a análise dos corpos ou os ensaios de arquivo sem alterações relevantes.

Resultado local final: **1000 testes aprovados, 0 falhados, 20 subtestes aprovados** (Python 3.12, 89,50 s). Esta etapa acrescenta 41 casos contributivos e uma segunda variante do teste de arquivo WSGI: 42 novos testes desde a suite de 958. O arquivo real foi construído pela rotina existente e o endpoint executado fora do checkout em instalação isolada, com e sem declarações laborais. `git diff --check` aprovado. Mantém-se um aviso herdado Starlette/httpx; não houve alteração de dependências.
