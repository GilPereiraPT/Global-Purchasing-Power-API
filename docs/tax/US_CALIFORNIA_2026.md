> Update 2026-10-04: the access failures below describe the earlier attempt. See US_2026_SOURCE_INTEGRATION.md and data/us_tax_2026_source_evidence.json for current scoped review and acquisition results. Net remains unavailable.

# Califórnia 2026 — FTB indisponível, SDI separado

Componente offline app/us_tax_california.py, branch independente da main d2e0fdb
após PR #29. Motor fiscal central/endpoints/preview antigo não são alterados.
Cenário restrito: empregado solteiro, residente CA todo o ano, sem dependentes,
apenas salário. Não existe net activado nem referência de liquidação completa.

## Fontes oficiais candidatas e estado

Em 4 de outubro de 2026, os três GET falharam com ProxyError, sem resposta HTTP,
originais ou SHA-256 de legislação:
- https://www.ftb.ca.gov/forms/2026/2026-540-tax-rate-schedules.pdf
- https://www.ftb.ca.gov/forms/2026/2026-540-booklet.html
- https://edd.ca.gov/en/payroll_taxes/rates_and_withholding/

Os paths FTB 2026 são candidatos não confirmados; falha de rede não demonstra
que as tabelas não foram publicadas. Nem tabelas de withholding EDD nem valores
FTB de 2025 substituem annual 2026. Não se introduziram escalões, dedução,
personal exemption credits, créditos de baixo rendimento ou imposto adicional
sobre rendimentos elevados sem dados oficiais. Todos ficam null, não zero.
É necessário verificar ajustes ao AGI, bases e fases de eliminação dos créditos,
e o imposto adicional/limiar efectivamente aplicável ao ano e taxable income.

O PR #29 documenta SDI 2026 1,3% sem wage ceiling. Preserva-se apenas como
**ilustração herdada não revalidada**, separada do income tax e do SDI final.
Exemplos aritméticos: 100000 → 1300, 200000 → 2600; 5 → 0,065 bruto, exibido
0,07 com ROUND_HALF_UP. Não se cria tecto pela antiga regra nem se afirma que
a multiplicação anual reproduz a soma de rounding por paycheck.

Toda a ilustração assume wages integralmente SDI-covered, plano estadual comum,
sem voluntary plan/exemption. Taxable wages podem diferir do bruto; faltam
cobertura, períodos, taxable base e regras de arredondamento/cobrança. Não se
considera uma contribuição completa/validada apenas por a taxa já existir no
legado. Income_tax, employee_contributions e net_income finais permanecem null.

## Testes, limites e desbloqueio

Decimal e strings monetárias; testes de produtos manuais independentes da taxa
herdada, half-cent/antes/depois, ausência de tecto, invalid inputs e ano/cenário
não suportados. Em baixos rendimentos e junto de 1 milhão (abaixo/exacto/acima)
verificam que brackets/credits/additional tax não viram zero nem 2025 se torna
2026. Estes são testes da protecção, não limites oficiais FTB validados.

Para completar, fornecer originais 2026 rate schedules/540 instructions,
exemption/other credits, ajustes, additional high-income tax e EDD rate/base/
rounding/coverage, via rede autorizada, com URL/timestamp/versão/SHA-256. Criar
reference returns oficiais independentes só depois dessa validação. O módulo
não se liga automaticamente ao adaptador federal nem modifica liquidação/API.
Sem merge, deployment, dados produtivos, alterações salariais/fiscais legadas
ou Android. Resultados da suite completa registados abaixo e na PR.

Suite completa: 683 passed, 1 warning, 20 subtests passed in 88.51s (0:01:28).
