# Pensilvânia 2026 — base, benefícios, UC e locais separados

Componente offline app/us_tax_pennsylvania.py; branch da main d2e0fdb após PR29.
Não altera o motor central, taxas legadas, endpoints ou Portugal. Cenário:
residente PA todo o ano, single, sem dependentes, apenas salário. **partial,
net_income null**, mesmo quando todos os inputs opcionais são preenchidos;
a evidência legal continua insuficiente. Não promete liquidação final.

## Fontes oficiais candidatas e acesso em 4 de outubro de 2026

Todos os GET falharam com ProxyError, sem HTTP, corpo original ou SHA-256:
- https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax
- https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax/tax-forgiveness
- https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/personal-income-tax/working-pennsylvanians-tax-credit
- https://www.pa.gov/agencies/dli/programs-services/unemployment/for-employers/uc-tax-information
- https://www.phila.gov/services/payments-assistance-taxes/taxes/income-taxes/wage-tax-salaried-employees/

Paths de benefícios/UC são candidatos: layout/existência não provados pela falha
de rede. O PR29 já documenta a taxa de 3,07% antes de créditos e sem standard
deduction/personal exemption. Conserva-se como ilustração herdada; não se
implementam limites/percentagens de benefícios nem UC a partir de memória.

## Bruto não é automaticamente remuneração tributável

O input `taxable_compensation` é obrigatório para produzir o preview novo de
3,07%; missing permanece null. Precisa de determinação PA independente:
compensação tributável, exclusões de benefícios Section125, despesas admissíveis
não reembolsadas, tratamento estadual da reforma/contribuições e diferenças do
federal W-2. Não aplicar standard deduction federal ou assumir que 401(k) reduz
PA taxable wages. Se zero é determinado explicitamente, aceita-se zero; não
preencher missing com zero. Neste cenário a base não pode exceder o bruto.
Exemplos aritméticos: bruto100000/base90000 → ilustração2763; base100000 →3070.
Isto não constitui aprovação das exclusões que originaram a base90000.

`forgiveness_eligibility_income` é input diferente: pode abranger rendimentos
não tributáveis/benefícios e regras household, não deriva só de taxable wages.
Tax Forgiveness exige instruções Schedule SP anuais e estatuto do próprio como
dependente, definição de eligibility income e escalões/fases aplicáveis ao
single sem dependentes. Nenhuma tabela é inferida dos rendimentos de teste.

Working Pennsylvanians Tax Credit precisa de regra exacta 2026, elegibilidade e
valor federal EITC determinado de forma independente. `federal_eitc` ausente é
null; zero explícito é distinguido, mas não activa crédito/final tax. Sem filhos
não equivale a EITC zero. Dedução/crédito estatal final e todos os benefícios
permanecem null até validar regras e factos; não se duplica um benefício.

## Contribuições e localidades

Employee unemployment (UC) é componente obrigatória separada, com rate/base e
pay-period rounding a verificar, não zero por desconhecimento. A sua base pode
diferir de PA taxable compensation; não se calcula UC com a base fiscal por
analogia. Não introduzir taxa candidata não documentada nas fontes obtidas.

Inputs `residence_psd` e `work_psd` (seis dígitos ASCII) distinguem locais de
residência e trabalho. São necessários municípios, distrito escolar, regras de
sourcing/reciprocidade e datas; PSD sozinho não verifica taxa. Local EIT, local
services tax e Philadelphia wage tax são componentes separadas/null. Não copiar
uma taxa Philadelphia para outros municípios nem assumir zero quando falta
localidade; verificar taxas anuais e alterações intra-ano, resident/nonresident,
isenções/low-income relief e créditos entre jurisdições. A selecção explícita de
PSD também não resolve a ausência de fonte oficial.

## Precisão, testes e validação pendente

Decimal/strings monetárias; cents ROUND_HALF_UP só como apresentação anualizada,
não legal rounding de liquidação/payroll. Schedule antes de créditos é anual,
não withholding. Tests manual arithmetic de 3,07% e rounding, base zero/explícita,
baixos/elevados, benefícios desconhecidos, contribuições/locais ausentes,
Philadelphia PSD, invalid inputs e distinção missing/zero. Rendimentos6500/9000
são probes, não limites oficiais de Tax Forgiveness validados. **Não existem
referências independentes de liquidação oficial** nesta entrega.

Para completar, obter manual PA2026/PA40/ScheduleSP, regras WPTC/federalEITC,
DLI employee UC e tabelas locais/Philadelphia com URL, versão, timestamp e
SHA-256, através de rede autorizada ou originais fornecidos. Rever exclusões/base
e dados necessários do trabalhador. Só então acrescentar referências e activar
componentes finais; integração no adaptador US não acontece automaticamente.
Sem merge/deploy, dados de produção, salários, Android ou configuração alterados.

Suite completa: **687 testes e 20 subtests aprovados, 0 falhas**, um aviso Starlette herdado.
