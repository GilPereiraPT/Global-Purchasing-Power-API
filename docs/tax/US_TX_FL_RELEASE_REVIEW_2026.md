# EUA 2026 — revisão TX/FL e condições para rendimento líquido

Consulta: **4 de outubro de 2026**. Base: main `6f5837b73babef810bd3dcf3779def82ca3a58cc` (PR #40 integrada); revisão da PR #41, sem comentários pendentes e CI inicial aprovado no commit `d47579e8d93baf2604abb6f54adb643fb5fd7dd3`.

**Não está concluída a fiscalidade dos EUA. Nenhum cenário norte-americano disponibiliza rendimento líquido total.** Os valores existentes são componentes anuais do modelo federal. Não são retenções, declarações fiscais liquidadas nem pagamentos mensais reais.

## Cobertura efetiva por cenário

| Estado | Cenário/ano | Federal | Estadual | Local | Contribuições estaduais do trabalhador | Líquido |
|---|---|---|---|---|---|---|
| Texas | solteiro, salário ordinário, 2026; factos completos | modelo federal condicionado | zero salarial fundamentado no parâmetro constitucional revisto | indisponível | desemprego e abrangência de regimes obrigatórios não validados | `partial`, `null` |
| Florida | mesmo cenário | modelo federal condicionado | zero salarial fundamentado na exclusão legal revista | indisponível | financiamento do reemployment pelo trabalhador proibido; completude dos restantes regimes não validada | `partial`, `null` |
| Nova Iorque | componente isolada: residente solteiro, apenas salário, 2026 | não integrado no cenário TX/FL | ilustração herdada até AGI 107650; não liquidação | NYC/Yonkers indisponíveis | DBL/PFL e condições indisponíveis | `partial`, `null` |
| Califórnia | componente isolada: mesmo agregado, 2026 | não integrado | tabelas anuais FTB, dedução, créditos e tributação adicional indisponíveis | não validado | parâmetro SDI 1,3% revisto; cobertura/arredondamento por pagamento indisponíveis | `partial`, `null` |
| Pensilvânia | componente isolada: mesmo agregado, 2026 | não integrado | 3,07% antes de créditos, apenas com remuneração tributável explícita | EIT/LST/Philadelphia indisponíveis | contribuição UC indisponível | `partial`, `null` |

O cenário API é `single_ordinary_wages_federal_benchmark`. A designação não significa que o resultado global seja `benchmark_estimate`. Continua `partial`. O cenário legado e os endpoints existentes são preservados. Ausência de região, factos, confirmação, bases divergentes ou condições fora do intervalo não autoriza cálculo líquido. Selecionar TX/FL não confirma automaticamente residência, local de trabalho ou emprego privado.

## Revisão das fórmulas federais

A integração dos escalões corresponde aos valores acumulados publicados na Rev. Proc. 2025-32, §4.01 Table 3: 1240, 5800, 17966, 41024, 58448 e 192979,25 USD nos limites tributáveis de 12400, 50400, 105700, 201775, 256225 e 640600 USD. Dedução padrão básica: 16100 (§4.14). O intervalo operacional termina em salário bruto 500000; o escalão tributável 640600 está apenas no teste existente dos parâmetros e não ativa esse rendimento no modelo.

AMTI restitui a dedução padrão; isenção 90100 e transição 244500 (§4.10); TMT aplica 26%/28%; AMT adicional é `max(0, TMT - imposto regular)`. Não se extrapola a redução de isenção acima de 500000. As instruções Form 6251 de 2025 sustentam apenas a estrutura; não substituem parâmetros anuais de 2026. Confirmar instruções finais de 2026 continua necessário para anunciar uma liquidação final.

Social Security: 6,2% até 184500; Medicare: 1,45% sem teto; Additional Medicare para solteiro: 0,9% acima de 200000. Publication 15 (2026), Topics 751/560, Publication 505 (2026) e a receita normativa sustentam os parâmetros anteriormente adquiridos. A nova tentativa SSA foi bloqueada; não se afirma nova validação independente SSA.

Créditos/deduções: EITC sem filhos fica zero apenas no intervalo explicitamente limitado a partir de 19540 e no cenário sem outro rendimento. Idade 25–64, não cego/não dependente, elegibilidade SSN declarada, bases federais/FICA iguais ao bruto, tips/overtime/charity zero e confirmação do modelo são obrigatórios. Essa confirmação exclui outros rendimentos, deduções, créditos, preferências AMT e impostos especiais; não prova elegibilidade pessoal. EITC reembolsável, deduções especiais e salário acima de 500000 não estão implementados.

Todos os montantes são `Decimal` e strings monetárias. Os cêntimos usam ROUND_HALF_UP apenas na apresentação: não reproduzem tax tables finais nem a soma dos arredondamentos por período salarial. Não substituir esses limites por uma alegação de arredondamento legal completo.

## Fontes, evidência e impedimentos concretos

A evidência previamente adquirida está em `data/us_tax_2026_source_evidence.json`: URL original/final, ano aplicável, data, tamanho, SHA-256 e âmbito. Mantém `parameters_reviewed`, não é promovida a `verified` só por ter checksum. Não foram encontrados os ficheiros brutos anteriores neste ambiente; os seus hashes não foram recalculados nesta revisão.

- TX: Texas Legislative Council, `https://tlc.texas.gov/docs/legref/TxConst.pdf`, artigo VIII §24-a: proibição de imposto sobre rendimento líquido individual. Fundamenta apenas a componente salarial estadual, não todas as deduções.
- FL: `https://www.flsenate.gov/Laws/Statutes/2026/220.02`, exclusão de pessoas singulares; `https://www.flsenate.gov/Laws/Statutes/2026/443.041`, proibição de transferir para empregados o financiamento das contribuições patronais de reemployment. Este último zero não é o total das contribuições estaduais.
- IRS: `https://www.irs.gov/irb/2025-45_IRB`, `https://www.irs.gov/publications/p15`, `https://www.irs.gov/taxtopics/tc560`, `https://www.irs.gov/instructions/i6251`, `https://www.irs.gov/publications/p505`.

Novas tentativas, registadas em `us_2026_jurisdiction_access.json`, foram recusadas pelo gateway HTTP (túnel 403; não é prova de indisponibilidade da fonte oficial):

1. TX Tax Code capítulo 302, Labor Code capítulo 204 e TWC: verificar proibições/competência tributária local e não transferência de contribuições de desemprego. Sem estes textos e confirmação de âmbito do emprego, não atribuir zero local/contributivo global.
2. FL constituição, competência local e §166.231: verificar impostos locais aplicáveis ao rendimento salarial, não confundir ausência de PIT estadual com ausência de todos os encargos. Delimitar trabalhadores privados ordinários versus regimes públicos/ocupacionais obrigatórios.
3. SSA COLA factsheet 2026: confirmar diretamente taxa/teto/base de cobertura, além da corroboração IRS existente.
4. NY: obter tabela anual final de 2026, lei §601/recapture acima de 107650, créditos, residência/trabalho NYC/Yonkers, DBL/PFL e períodos/pagamento patronal. Localidade ausente impede o total mesmo que o imposto estadual seja calculável.
5. CA: obter tabela anual final FTB 2026, dedução padrão, exemption credits, ajustes, imposto adicional de rendimentos elevados e base; EDD SDI cobertura/exceções e regras periódicas. Tabelas de retenção não são substitutos.
6. PA: obter regras 2026 Tax Forgiveness, Working Pennsylvanians Tax Credit/elegibilidade federal EITC, UC do trabalhador e diferenças de remuneração tributável; PSD de residência/trabalho, taxas locais e datas de Philadelphia. A taxa geral não resolve esses componentes.

Procedimento alternativo: um revisor pode descarregar diretamente os documentos oficiais identificados, incluindo instruções anuais e textos legais vigentes, e fornecê-los como anexos privados com URL, data e ano/versão. Rever os documentos e os cálculos independentemente antes de promover qualquer cenário. Não contornar o bloqueio com estimativas, páginas não oficiais ou tabelas de outro ano.

## Parâmetros, BD e atualização sem terminal

Os parâmetros fiscais deste modelo residem em `app/tax_components.py`, `app/us_federal_benchmark.py` e nos adaptadores estaduais; a evidência está em JSON runtime. Os endpoints `/v1/tax/*` calculam diretamente com esses módulos: não importam nem atualizam uma tabela fiscal SQLite. `app/store.py` contém uma cache de respostas, não uma BD normativa. As tabelas de salários e o mecanismo de publicação bulk não são destinos para estes parâmetros.

**Não é necessária uma migração ou pacote de dados nesta alteração.** Não carregar o JSON de evidência como pacote salarial. Não há importação nem reversão de dados fiscais/salariais a executar. Os arquivos permitidos pelo sistema existente incluem módulos Python e JSON runtime; o novo módulo está abrangido sem alterar deployment. O teste do arquivo real executa WSGI numa instalação temporária, sem criar as bases ativas.

Para uma futura atualização autorizada, após revisão/merge por quem tenha essa responsabilidade (não efetuados nesta tarefa):

1. No GitHub, confirmar aprovação da PR, CI verde e anotar o SHA exato integrado. Não ativar SSH nem agendamentos para esta operação.
2. No Data Manager existente, consultar estado/espaço/permissões; criar backup privado e executar «Testar recuperação». Uma cópia existente não prova recuperação.
3. Usar o controlo existente de atualização da API, com autorização administrativa e confirmação. Atualiza apenas a main cujo CI tenha passado; não pode instalar esta PR aberta. Não utilizar publicação salarial, importação ou inventário para atualizar regras fiscais.
4. No cPanel, se necessário, usar o controlo de reinício da aplicação Python/Passenger. Confirmar `/v1/health`: saúde e SHA exato esperado. Não alterar token, configuração ou bases SQLite.
5. Verificar `/v1/tax/assumptions/US` e consultas TX/FL com factos explícitos: devem continuar parciais nesta versão. Se falhar saúde/paridade, não anunciar sucesso; guardar o identificador da cópia de código pré-atualização e pedir reversão do runtime pelo procedimento existente. Não restaurar bases ativas para reverter regras em código; a recuperação de código é diferente da recuperação SQLite. A interface atual não acrescenta nesta PR um botão de rollback de código; se necessário, a assistência do operador do alojamento continua a ser um requisito concreto, não uma operação disponível ao utilizador no painel.

Nenhuma destas operações foi realizada na produção.

## Validação

Base: 902 testes + 20 subtestes aprovados. Os novos testes usam valores acumulados publicados no IRS e referências FICA fixas, fronteiras adjacentes e arredondamento de apresentação; não são liquidações oficiais independentes. Cobrem evidência ausente, preservação de desconhecidos, isolamento dos metadados, paridade TX/FL/NY/CA/PA/sem região e arquivo real WSGI isolado. Os casos independentes de **líquido completo**, incluindo a validação jurídica local e contributiva, ainda são um bloqueio. Não apresentar o saldo federal como esse líquido.
