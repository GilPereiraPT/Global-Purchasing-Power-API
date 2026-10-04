> Update 2026-10-04: the access failures below describe the earlier attempt. See US_2026_SOURCE_INTEGRATION.md and data/us_tax_2026_source_evidence.json for current scoped review and acquisition results. Net remains unavailable.

# Nova Iorque 2026 — componente anual parcial

Base main d2e0fdb após PR #29. app/us_tax_new_york.py não altera o motor central,
endpoints, Portugal ou a simulação legada. É componente offline importável;
a integração/activação futura exige validação, não acontece por importação.
Cenário: single, residente NY todo o ano, sem dependentes, apenas salário.

## Fontes oficiais e bloqueios — 4 de outubro de 2026

GETs abaixo falharam com ProxyError, sem HTTP/corpo/checksum de legislação:
- https://www.nysenate.gov/legislation/laws/TAX/601 — história 2026, single,
  escalões e supplemental tax/recapture.
- https://www.tax.ny.gov/pit/file/tax-tables/2026.htm — destino candidato anual;
  existência/layout não confirmados. Não usar IT-2104 (retenção) para validar
  dedução/liquidação anual.
- https://www.tax.ny.gov/pit/credits/household_credit.htm — household credit;
  também faltam earned income credit e créditos locais aplicáveis.
- https://www.wcb.ny.gov/content/main/DisabilityBenefits/Employer/WhoPaysBenefits.jsp
  — DBL, cobertura e contribuição employee versus financiamento employer.
- https://paidfamilyleave.ny.gov/2026 — PFL taxa/base/tecto 2026 e excepções.

A tabela é herdada do PR #29 e rotulada ilustração não revalidada. Preserva
bases legais arredondadas: 0/3,9% até taxable 8500; 332/4,4% sobre 8500 até
11700; 473/5,15% sobre 11700 até 13900; 586/5,4% sobre 13900 até 80650;
4191/5,9% acima daí dentro do limite de AGI. Não reintegrar marginalmente esses
interceptos: no limiar 8500 dá 331,50; logo acima usa base 332, como no legado.
Ilustração assume NY AGI igual ao bruto, sem ajustes e não-dependente de outro
filer, dedução candidata 8000. Essa dedução/factos precisam de validação anual.

**Acima de AGI 107650 o schedule é null**, não se extrapola. Supplemental/
recapture e faixas superiores permanecem indisponíveis até consultar lei e
instruções. Créditos não são zero: sem dependentes não resolve elegibilidade
EITC/household/NYC, dependência do próprio ou rendimentos elegíveis.

NYC income tax, Yonkers resident surcharge e Yonkers nonresident earnings tax
são componentes separadas. Precisam de residência E trabalho/localização e
história/sourcing quando pertinente. Localidade other não implica zero sem
prova legal. DBL/PFL precisam de cobertura, empregador e períodos; não assumir
zero nem introduzir taxas de memória. Valores finais income_tax,
employee_contributions e net_income sempre null; partial ou unavailable.

Decimal/strings, cents ROUND_HALF_UP só na apresentação, não rounding legal
anual/payroll. Componentes não são retenções salariais. Testes de aritmética
manual herdada incluem todos os limites disponíveis, recapture, baixo/elevado,
localidades ausentes/NYC/Yonkers e invalid inputs. Não são reference returns
oficiais: ainda não há validação independente de liquidação.

Para desbloquear, obter originais históricos 2026, instruções/tabelas, créditos,
NYC/Yonkers e regras WCB/PFL numa rede autorizada, com URL, versão, timestamp e
SHA-256. Só então implementar componentes em falta/referências oficiais e
activar resultados. Não houve alterações de produção, merge ou deployment.

Suite completa: **693 testes e 20 subtests aprovados, 0 falhas**, um aviso Starlette herdado.
