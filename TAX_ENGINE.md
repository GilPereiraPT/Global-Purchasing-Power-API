# Motor de salário líquido — Fase 3B

## Estado atual

O modelo português de 2025 passou de indisponível a **parcial**: existem agora
componentes fiscais implementados e testados contra documentação oficial da AT.
**O IRS final anual, as contribuições do trabalhador e o salário líquido continuam
indisponíveis.** Não há ano ou cenário português anunciado como integralmente
suportado: `supported_tax_years` e `available_countries` continuam vazios.

O Portal das Finanças tornou-se acessível nesta fase. Foram consultadas a página
explicitamente dedicada aos rendimentos de 2025, as versões históricas de dezembro
de 2025 dos artigos 68.º e 70.º e o diploma da Lei n.º 55-A/2025. O guia da Segurança
Social fornecido não foi obtido como documento válido: o endereço sem `www`
devolveu 503/timeout; a variante com `www` redirecionou para HTML da Segurança
Social Direta. A alternativa `www.seg-social.gov.pt` foi bloqueada pelo proxy.
O Diário da República respondeu com uma aplicação JavaScript, sem fornecer o
texto contributivo que permitisse validar o regime histórico.

Não foi ativada uma taxa contributiva de 11% com base em memória ou fontes de
terceiros. Não foram presumidos créditos ou despesas do contribuinte a zero.

## Arquitetura e âmbito

- `app/tax_engine.py`: pedidos imutáveis, protocolo de adaptadores por país,
  registo, validação partilhada, `Decimal` e proteção contra resultados completos
  sem componentes/proveniência suficientes.
- `app/tax_portugal.py`: controlo explícito do país, cenário, região e ano; só
  devolve os componentes de 2025 no cenário continental reconhecido.
- `app/tax_portugal_2025.py`: componentes oficiais de 2025, funções puras e fontes.
- `docs/tax/portugal_2025_sources.json`: URLs, âmbito, data de consulta, excertos e
  SHA-256 dos documentos obtidos. Os hashes identificam os documentos consultados;
  não constituem uma validação automática de futuras versões dessas páginas.
- FastAPI e WSGI usam o mesmo serviço; o overview/comparação selecionam o motor
  explicitamente. Os pedidos e o endpoint fiscal legados mantêm o comportamento.

Os módulos continuam como ficheiros diretos de `app/`, compatíveis com o pacote
existente. Não se alterou o deployment ou o Android.

Cenário: `single_employee_no_dependents`, região fiscal explícita `mainland`:
residente fiscal durante todo o ano, adulto solteiro, sem dependentes/deficiência,
apenas categoria A, regime geral, bruto integralmente sujeito a contribuições,
sem IRS Jovem/RNH/IFICI e sem outros rendimentos. Excluem-se quotizações sindicais,
ordens profissionais e indemnizações de rescisão. Estes pressupostos delimitam o
cenário; **não declaram inexistentes despesas gerais ou outros créditos pessoais**.

Casados, dependentes, ilhas e regimes especiais continuam sem cobertura. Não se
calculam contribuições patronais, retenção mensal, reembolsos/acertos com retenções,
pagamentos efetivos em 12/14 meses ou poder de compra líquido internacional.

## Componentes verificados para 2025

### Categoria A — artigo 25.º

Dedução específica padrão: **4 462,15 €**, correspondente a 8,54 × IAS de 522,50 €.
No âmbito restrito, a dedução é o menor entre o bruto e o maior entre este limite
e as contribuições obrigatórias efetivamente conhecidas. Não se deduzem novamente
as contribuições ao rendimento coletável depois de já terem substituído a dedução
específica.

`specific_deduction(gross, mandatory_contributions)` exige o montante efetivo das
contribuições. Se for desconhecido, devolve `None`. A API publica o limite padrão,
mas não o apresenta como a dedução efetiva do utilizador.

### Escalões anuais — artigo 68.º e Lei n.º 55-A/2025

Tabela prática publicada pela AT para os rendimentos de 2025:

| Rendimento coletável até (€) | Taxa normal | Parcela a abater (€) |
| --- | --- | --- |
| 8 059 | 12,50% | 0,00 |
| 12 160 | 16,00% | 282,07 |
| 17 233 | 21,50% | 950,91 |
| 22 306 | 24,40% | 1 450,67 |
| 28 400 | 31,40% | 3 011,98 |
| 41 629 | 34,90% | 4 006,10 |
| 44 987 | 43,10% | 7 419,54 |
| 83 696 | 44,60% | 8 094,51 |
| Superior a 83 696 | 48,00% | 10 939,90 |

`practical_general_collection(taxable)` aplica rendimento coletável × taxa normal
− parcela a abater da tabela prática. **É coleta prática antes de créditos, não
IRS final.** O módulo conserva também as taxas médias publicadas no artigo 68.º.
Não usa as taxas iniciais de 2025 nem os limites de 2026.

A tabela prática tem coeficientes arredondados e pequenas descontinuidades nos
limites. Os testes reproduzem os valores publicados, sem suavizações inventadas.
Ainda é necessário reconciliar este método com o artigo 68.º, n.º 2, e a precisão
utilizada pela AT na liquidação. Não se promove este componente a imposto final.

### Mínimo de existência — artigo 70.º histórico

Para um único sujeito passivo, exclusivamente categoria A:

- IAS de 2025: **522,50 €**.
- Valor de referência (VR): **12 180 €**, não os 12 880 € do texto atual.
- Limite L publicado nas fórmulas simplificadas da AT: **13 863,06 €**.
- Limite de exclusão: bruto superior a **16 093 €** (2,2 × 14 × IAS).
- Limite das despesas gerais usado na fórmula: **250 €**; este parâmetro legal não
  significa que o contribuinte tenha direito a um crédito efetivo de 250 €.

Com RB = bruto e DE = dedução específica conhecida, o abatimento bruto é:

1. RB ≤ 12 180: `12180 − DE − 250/0.125`.
2. 12 180 < RB ≤ 13 863,06: `12180 − 2.6×(RB−12180) − DE − 250/0.125`.
3. RB > 13 863,06: `13863.06 − 8059 − 1.35×(RB−13863.06) − DE`.

O resultado é limitado entre zero e RB−DE. Acima de 16 093 € o abatimento não se
aplica. As outras exclusões do artigo 70.º ficam fora do âmbito porque o cenário
exclui outros rendimentos e outros titulares.

O módulo aplica as **fórmulas simplificadas publicadas** com L = 13 863,06. Não
presume que arredondar L a duas casas seja a convenção legal interna da liquidação.
A equivalência com a fórmula legislativa e o seu arredondamento continua pendente.

### Solidariedade — artigo 68.º-A

`solidarity_collection(taxable)` calcula 2,5% da parcela entre 80 000 e 250 000 €,
mais 5% do excedente de 250 000 €. Os limiares respeitam ao **rendimento coletável**,
não ao bruto. Para bruto até 80 000 €, no cenário restrito, é possível provar a
não aplicação da solidariedade sem estimar a base coletável.

### Despesas gerais familiares — artigo 78.º-B

`general_expense_credit(eligible_expenses)` calcula 35% das despesas elegíveis
conhecidas, com limite de 250 €. `None` continua `None`: nem zero nem o limite
máximo são atribuídos por defeito. Elegibilidade e montantes efetivos dependem de
faturas e identificação fiscal; a API atual não recebe esses dados.

## Aritmética e arredondamento

Todos os componentes usam `Decimal`, com contexto local de precisão 40 nas
operações. Não há conversão para float. As funções conservam resultados não
arredondados; não se arredonda cada escalão ou operação intermédia.

A API usa strings com duas casas para valores monetários apresentados. O
`ROUND_HALF_UP` genérico é uma convenção de **apresentação**, não uma afirmação
sobre o arredondamento legal do IRS. Não foi encontrada/validada a especificação
completa do arredondamento da liquidação anual. Esse bloqueio impede a ativação
do IRS final, mesmo que as restantes fórmulas fossem suficientes.

O futuro `monthly_equivalent_12` será o líquido anual dividido por 12. Não será
retenção mensal, recibo de vencimento nem descrição dos pagamentos de subsídios.

## API versionada — FastAPI e WSGI

| Método e caminho | Função |
| --- | --- |
| `GET /v1/tax/countries` | Adaptadores, cenários e países integralmente disponíveis |
| `GET /v1/tax/years/{country}` | Anos integralmente suportados |
| `GET /v1/tax/assumptions/{country}` | Pressupostos, limitações e fontes dos componentes |
| `GET /v1/tax/calculate` | Pedido anual explícito |

```text
/v1/tax/calculate?country=PT&annual_gross=30000&tax_year=2025&scenario=single_employee_no_dependents&region=mainland
```

Devolve `status: partial`, `income_tax: null`, `employee_social_security: null`,
`net_income: null` e `monthly_equivalent_12: null`. O campo adicional `components`
identifica valores conhecidos e desconhecidos. Neste exemplo o abatimento por
mínimo de existência e a solidariedade são comprovadamente zero; a dedução
específica efetiva, os créditos e o IRS final continuam desconhecidos.

`verified_component_sources` e `validated_component_tax_years: [2025]` nos
metadados distinguem componentes confirmados de anos integralmente suportados.
Outros anos, regiões e cenários devolvem `unavailable`, sem reutilizar os
componentes de 2025. Fontes verificadas registam URL, ano, âmbito e data.

`country`, `annual_gross`, `tax_year` e `scenario` são obrigatórios. O bruto deve
ser positivo, ter no máximo duas casas e não exceder 100 000 000. Entradas inválidas,
parâmetros de cálculo inesperados ou duplicados recebem 422; falta de cobertura
fiscal recebe 200 com `unavailable`. `partial` nunca expõe líquido.

Overview: selecionar `tax_scenario`, `tax_region`, `net_tax_year` e bruto explícito.
O ano não é inferido do default fiscal legado ou da observação salarial. Na
comparação, os mesmos parâmetros têm sufixos `_a` e `_b` e são independentes.
`region` continua a descrever os dados salariais; `tax_region`, a jurisdição fiscal.
`/v1/tax-components/{country}` e os pedidos existentes permanecem intactos.

## Validação e passos para completar

Os testes cobrem todos os limites de escalão da tabela prática (abaixo, no limite,
acima), substituição/cap da dedução específica, ramos e limites do mínimo,
solidariedade, despesas conhecidas/desconhecidas, precisão Decimal, proveniência,
paridade FastAPI/WSGI e indisponibilidade do líquido em todos os casos incompletos.

Há referências numéricas independentes para **componentes** e uma cadeia com
contribuições explicitamente fornecidas. Por exemplo: bruto 30 000 €, contribuições
conhecidas de 3 300 €, DE 4 462,15 €, mínimo zero, coletável 25 537,85 € e coleta
prática não arredondada de 5 006,9049 €. Os 3 300 € são um dado de entrada do caso,
não prova de uma taxa contributiva de 11%. O valor não é IRS final nem permite
publicar um líquido validado.

**Ainda não existem casos anuais completos de referência validados.** Para os
concluir e ativar `verified`, falta:

1. Obter documentação oficial válida do regime contributivo aplicável em 2025:
   taxa, base de incidência, exceções, periodicidade e arredondamento. Não é
   suficiente multiplicar o bruto anual por uma taxa presumida.
2. Validar os dados de créditos pessoais/despesas e as deduções à coleta aplicáveis,
   incluindo a forma explícita de receber esses dados na API.
3. Confirmar arredondamento legal da liquidação e equivalência entre tabela prática,
   taxas médias e fórmulas simplificadas do mínimo de existência.
4. Criar referências anuais completas independentemente calculadas para os
   limiares, rendimentos baixos/altos e solidariedade.

Não são necessários novos segredos ou alterações ao deployment. Para avançar,
é necessário um documento oficial contributivo acessível e a especificação de
liquidação/precisão da AT; podem ser usadas cópias oficiais verificáveis com
identificação da versão e vigência de 2025.

## Resultados de execução — Fase 3B

```text
.venv/bin/python -m pytest -q
444 passed, 1 warning in 69.58s
```

**444 aprovados, 0 falhados**, incluindo 98 testes novos nesta fase (346 na entrega
anterior). Os testes anteriores foram conservados; as expectativas do cenário
PT/2025 foram atualizadas de `unavailable` para `partial`, mantendo as verificações
que impedem líquido e contribuições inventadas. Os testes específicos do motor,
API e componentes somam 179 aprovados.

O único aviso é o `StarletteDeprecationWarning` preexistente relativo a `httpx`
no TestClient. Não foram alteradas dependências para resolver esse assunto fora
do âmbito.

A implementação mantém-se na branch `feat/portugal-net-salary` e na PR #13 em
rascunho. Não houve merge, deployment ou alteração ao Android, ao sistema de
deployment, a segredos ou a bases de dados de produção.
