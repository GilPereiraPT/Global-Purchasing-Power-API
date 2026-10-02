# Motor de salário líquido — Fase 3C

## Estado atual

O modelo português de 2025 passou de indisponível a **parcial**: existem agora
componentes fiscais implementados e testados contra documentação oficial da AT.
**O IRS final anual, as contribuições do trabalhador e o salário líquido continuam
indisponíveis.** Não há ano ou cenário português anunciado como integralmente
suportado: `supported_tax_years` e `available_countries` continuam vazios.

Nesta fase foram confirmados no Diário da República os artigos 13.º, 44.º e
53.º do Código Contributivo: aplicação da taxa à base remuneratória e **11% a cargo
do trabalhador no regime geral**. A taxa está implementada, sem descontos por
deficiência. O artigo 109.º também mantém 11% para o trabalhador; a redução ali
indicada é patronal. Os regimes especiais continuam excluídos.

A publicação original da Lei n.º 110/2009 foi comparada com os artigos não
alterados da consolidação oficial. As redações com efeitos apenas em janeiro de
2026 não foram usadas no modelo de 2025. Também foi obtido o guia oficial
«Declaração de Remunerações», versão 2016–V5.36, publicado em 14 de janeiro de 2025
(e atualizado em setembro de 2025 no catálogo público). O identificador 2016 é o
número do guia, não o ano fiscal.

**Continua por validar a convenção de arredondamento monetário das quotizações e
a agregação dos montantes periódicos num total anual.** Nem os artigos consultados,
nem o Decreto Regulamentar n.º 1-A/2011, nem o guia obtido forneceram a especificação
necessária. A regra de arredondamento de taxas do artigo 56.º, n.º 3, não é uma regra
de arredondamento de montantes das quotizações e não foi usada como tal.

As despesas gerais elegíveis podem agora ser fornecidas explicitamente. Não são
presumidos a zero os restantes créditos ou deduções pessoais desconhecidos. O
arredondamento final/intermédio do IRS também continua sem validação suficiente.

## Arquitetura e âmbito

- `app/tax_engine.py`: pedidos imutáveis, protocolo de adaptadores por país,
  registo, validação partilhada, `Decimal` e proteção contra resultados completos
  sem componentes/proveniência suficientes.
- `app/tax_portugal.py`: controlo explícito do país, cenário, região e ano; só
  devolve os componentes de 2025 no cenário continental reconhecido.
- `app/tax_portugal_2025.py`: componentes oficiais de 2025, taxa contributiva geral, métodos legislativos e práticos separados, funções puras e fontes.
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

### Segurança Social — Código Contributivo

`employee_contribution_unrounded(contribution_base)` aplica **11%** a uma base
conhecida integralmente sujeita. Mantém precisão Decimal, sem inventar arredondamento
anual. O bruto do cenário exclui prestações isentas e bases convencionais; não se
presume que todo o rendimento da categoria A, fora deste cenário, esteja sujeito
à Segurança Social.

A taxa e o produto não arredondado são publicados como componentes. O produto
anual **não é apresentado como a soma das quotizações efetivamente descontadas**.
Essa soma depende dos períodos/bases contributivos e da convenção de arredondamento,
que falta confirmar. `employee_social_security` continua `null` no resultado anual.
Não se inferem pagamentos iguais em 12 ou 14 meses.

Fontes: Código Contributivo, artigos 13.º, 44.º, 46.º e 53.º; publicação original da
Lei n.º 110/2009 e correspondência com os artigos aplicáveis em 2025. O artigo
109.º foi consultado para impedir a atribuição automática de uma taxa reduzida ao
trabalhador com deficiência; esse cenário não está coberto no IRS inicial.

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
IRS final.** `statutory_general_collection(taxable)` implementa separadamente o desdobramento
do artigo 68.º, n.º 2: limite do escalão anterior × taxa média B, mais excedente ×
taxa normal A do escalão aplicável. Conserva o valor não arredondado. Não substitui
a fórmula legislativa por uma integração genérica de taxas A ou pelas parcelas
arredondadas da tabela prática.
Não usa as taxas iniciais de 2025 nem os limites de 2026.

A tabela prática tem coeficientes arredondados e pequenas descontinuidades nos
limites. Os testes reproduzem os valores publicados, sem suavizações inventadas.
Os dois métodos estão agora separados e testados. Falta validar a precisão
intermédia/final e os casos de controlo da liquidação da AT, incluindo os limites
exatos dos escalões. Não se promove este componente a imposto final.

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
`statutory_minimum_existence_abatement` usa separadamente a fórmula legislativa
sem arredondar L: `12180 − 250/(0.125×3.6) + 8059/3.6 = 249535/18`. Assim, L é
aproximadamente 13 863,055555…; um bruto de 13 863,06 já fica acima desse limite
não arredondado. Os testes comparam as duas variantes com aritmética racional.
A precisão que a AT efetivamente utiliza na liquidação continua por validar.

### Solidariedade — artigo 68.º-A

`solidarity_collection(taxable)` calcula 2,5% da parcela entre 80 000 e 250 000 €,
mais 5% do excedente de 250 000 €. Os limiares respeitam ao **rendimento coletável**,
não ao bruto. Para bruto até 80 000 €, no cenário restrito, é possível provar a
não aplicação da solidariedade sem estimar a base coletável.

### Despesas gerais familiares — artigo 78.º-B

`general_expense_credit(eligible_expenses)` calcula 35% das despesas elegíveis
conhecidas, com limite de 250 €. A API recebe `eligible_household_expenses`,
montante anual das faturas elegíveis **exclusivamente do artigo 78.º-B**. Não inclui
saúde, educação ou habitação. `None` continua `None`: nem zero nem o limite
máximo são atribuídos por defeito. Elegibilidade e montantes efetivos dependem de
faturas e identificação fiscal; o valor fornecido pelo utilizador é uma declaração
de elegibilidade, não uma verificação automática das faturas. Outras categorias
de deduções/créditos não são inferidas deste campo.

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
/v1/tax/calculate?country=PT&annual_gross=30000&tax_year=2025&scenario=single_employee_no_dependents&region=mainland&eligible_household_expenses=1000
```

Devolve `status: partial`, `income_tax: null`, `employee_social_security: null`,
`net_income: null` e `monthly_equivalent_12: null`. O campo adicional `components`
identifica valores conhecidos e desconhecidos. Neste exemplo o abatimento por
mínimo de existência e a solidariedade são comprovadamente zero; a taxa de 11% e o crédito geral de 250 € são conhecidos. O total contributivo
monetário, a dedução específica efetiva e o IRS final continuam indisponíveis.
O produto contributivo não arredondado fica identificado como tal.

`verified_component_sources` e `validated_component_tax_years: [2025]` nos
metadados distinguem componentes confirmados de anos integralmente suportados.
Outros anos, regiões e cenários devolvem `unavailable`, sem reutilizar os
componentes de 2025. Fontes verificadas registam URL, ano, âmbito e data.

`country`, `annual_gross`, `tax_year` e `scenario` são obrigatórios. O bruto deve
ser positivo, ter no máximo duas casas e não exceder 100 000 000. Entradas inválidas,
parâmetros de cálculo inesperados ou duplicados recebem 422; falta de cobertura
fiscal recebe 200 com `unavailable`. `partial` nunca expõe líquido.

Overview: selecionar `tax_scenario`, `tax_region`, `net_tax_year`, bruto explícito
e, quando conhecido, `eligible_household_expenses`.
O ano não é inferido do default fiscal legado ou da observação salarial. Na
comparação, os mesmos parâmetros, incluindo `eligible_household_expenses_a/b`,
têm sufixos `_a` e `_b` e são independentes.
`region` continua a descrever os dados salariais; `tax_region`, a jurisdição fiscal.
`/v1/tax-components/{country}` e os pedidos existentes permanecem intactos.

## Validação e passos para completar

Os testes cobrem todos os limites de escalão da tabela prática (abaixo, no limite,
acima), substituição/cap da dedução específica, ramos e limites do mínimo,
solidariedade, despesas conhecidas/desconhecidas, precisão Decimal, proveniência,
paridade FastAPI/WSGI e indisponibilidade do líquido em todos os casos incompletos.

Há referências independentes, com `Fraction` e os coeficientes históricos
oficiais, para os cinco salários pedidos. Estão em
`docs/tax/portugal_2025_reference_components.json`. **São referências condicionais
de componentes; não são liquidações anuais completas validadas.**

Em todos os casos abaixo foram explicitamente fornecidas despesas gerais elegíveis
de 1 000 €, cujo crédito bruto é 250 €. A base coletável assume, para análise da
fórmula, que as quotizações anuais efetivas coincidem com o produto não arredondado
de 11%; esta condição ainda não está demonstrada para uma distribuição de pagamentos.

| Bruto anual (€) | Produto SS não arredondado (€) | Base coletável condicional (€) | Coleta art. 68 antes de créditos, não arredondada (€) | Solidariedade (€) |
| --- | --- | --- | --- | --- |
| 15 000 | 1 650 | 10 537,85 | 1 403,99100 | 0 |
| 25 000 | 2 750 | 20 537,85 | 3 560,56146 | 0 |
| 40 000 | 4 400 | 35 537,85 | 8 396,60565 | 0 |
| 60 000 | 6 600 | 53 400 | 15 721,88909 | 0 |
| 100 000 | 11 000 | 89 000 | 31 780,09584 | 225 |

Exemplo de diferença relevante: para 25 000 € brutos, a tabela prática produz
3 560,5654 €, mas o desdobramento com a taxa média publicada produz 3 560,56146 €.
Subtraindo o crédito de 250 € e aplicando apenas o arredondamento de apresentação,
os resultados diferem em um cêntimo: 3 310,57 € e 3 310,56 €. Não se escolheu um
IRS final silenciosamente.

**IRS final, líquido anual e equivalente mensal continuam nulos nos cinco casos.**
Os testes verificam essa proteção. A independência da aritmética e a confirmação
legislativa das componentes não substituem os dados/regras em falta.

Para concluir a Fase 3C e ativar `verified`, falta:

1. Validar o arredondamento monetário contributivo de 2025 e a forma de agregar
   quotizações periódicas. Determinar que dados de pagamentos são necessários,
   sem inventar uma distribuição em 12/14 pagamentos.
2. Validar todos os créditos/deduções aplicáveis ao cenário, ou restringir o cenário
   através de declarações explícitas e comprovadas sobre a sua não aplicação.
   Ter despesas gerais conhecidas não prova inexistência de outros créditos.
3. Validar a precisão/arredondamento da liquidação anual do IRS, incluindo taxas
   médias, limites exatos dos escalões e o L do mínimo de existência.
4. Obter casos anuais de controlo independentes que confirmem a liquidação e os
   totais contributivos dos cinco salários antes de publicar líquido.

Não houve alterações de segredos ou configuração de produção. Os portais oficiais
foram consultados com TLS verificado. A dificuldade restante não é apenas acesso:
a documentação obtida ainda não especifica todas as regras monetárias necessárias.
São necessários os requisitos técnicos oficiais de 2025 e referências de liquidação.

## Resultados de execução — Fase 3C

Comando: `.venv/bin/python -m pytest -q`. Resultado: **528 testes aprovados,
zero falhados**, em 72,44 segundos. Foram acrescentados 84 testes aos 444 da
entrega anterior. Existe um aviso de descontinuação do uso de `httpx` pelo
TestClient de Starlette; não afetou a execução. Não foram removidos os testes
existentes ou as proteções que impedem líquido incompleto.

A implementação mantém-se na branch `feat/portugal-net-salary` e na PR #13 em
rascunho. Não houve merge, deployment ou alteração ao Android, ao sistema de
deployment, a segredos ou a bases de dados de produção.
