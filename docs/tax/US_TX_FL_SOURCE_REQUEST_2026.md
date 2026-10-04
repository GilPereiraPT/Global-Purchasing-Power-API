# Documentos necessários para concluir Texas e Florida — 2026

Pedido de revisão de 4 de outubro de 2026, PR #41. **Nenhum líquido total foi ativado.** Todas as 13 consultas desta continuação foram recusadas pelo gateway do ambiente; a evidência das tentativas está em `us_tx_fl_followup_access.json`. Um erro do túnel não confirma nem desmente o conteúdo da fonte e não confirma que um endereço de documento anual esteja publicado.

## Cenário a validar

Empregado ordinário do setor privado, não ferroviário, solteiro, sem dependentes, residente fiscal dos EUA durante todo o ano de 2026, com residência e trabalho exclusivamente no mesmo estado selecionado (TX ou FL). Salário de um empregador; sem trabalho noutros estados, estatuto público, regime ocupacional especial, plano previdencial obrigatório, ordens judiciais de retenção ou outra circunstância fora deste cenário. As bases federal, Social Security e Medicare devem ser fornecidas e iguais ao bruto. Mantêm-se os factos e o intervalo federal existentes: idade 25–64, bruto 19540–500000, elegibilidade SSN declarada, sem tips/overtime/charity ou outras deduções/créditos especiais.

Este é o **âmbito proposto para a validação**, não uma extensão já autorizada dos factos da API. Atualmente o modelo não recolhe confirmação específica de emprego privado, residência/trabalho no mesmo estado e ausência de regimes obrigatórios especiais. Esses dados terão de ser explícitos e testados antes de ativar o líquido; a seleção do estado ou a confirmação federal não os substitui.

## O que fornecer primeiro

Fornecer os documentos completos abaixo como PDF ou HTML guardado a partir da fonte oficial. Conservar URL, título, data de obtenção e data de vigência; enviar o texto/versão aplicável a 2026, incluindo alterações com efeitos durante o ano. Capturas parciais, resumos de motores de pesquisa e tabelas de retenção não bastam. Não são necessários tokens, documentos pessoais, salários reais, configuração ou acesso à produção.

| Prioridade / documento oficial | URL | Regra que precisa de ser confirmada |
|---|---|---|
| 1 — Texas Tax Code, capítulo 302 | https://statutes.capitol.texas.gov/Docs/TX/htm/TX.302.htm | Texto e âmbito da proibição de imposto municipal sobre rendimento; confirmar alcance sobre o salário do residente e que não fica outra categoria local salarial por cobrir. Não extrapolar a proibição estadual para municípios sem esta revisão. |
| 1 — Texas Labor Code, capítulo 204 | https://statutes.capitol.texas.gov/Docs/LA/htm/LA.204.htm | Quem financia unemployment insurance e eventual proibição de cobrar/deduzir contribuições do trabalhador; vigência em 2026. O texto do capítulo deve permitir identificar a disposição exata, sem presumir o número de uma secção não lida. |
| 1 — Constituição da Florida, artigo VII §§1 e 5 | https://www.flsenate.gov/Laws/Constitution | Proibição/limites sobre rendimento de pessoas singulares residentes e competência tributária de municípios/condados. Confirmar conjuntamente que nenhuma autorização permite imposto salarial local neste cenário. |
| 1 — Florida Statutes 2026, §166.201 | https://www.flsenate.gov/Laws/Statutes/2026/166.201 | Limites da competência tributária municipal e necessidade de autorização geral; distinguir poder de cobrar taxas/serviços de imposto sobre salário. Isoladamente esta secção não prova ausência de todos os tributos locais. |
| 2 — Texas Labor Code, capítulos 406 e 415 | https://statutes.capitol.texas.gov/Docs/LA/htm/LA.406.htm e https://statutes.capitol.texas.gov/Docs/LA/htm/LA.415.htm | Âmbito do workers’ compensation para emprego privado; financiamento e eventual proibição de transferir prémios/custos para o trabalhador. Confirmar a disposição aplicável no texto, sem inventar uma secção. |
| 2 — Florida Statutes 2026, §440.21 | https://www.flsenate.gov/Laws/Statutes/2026/440.21 | Regra sobre acordos que fazem o empregado pagar prémios de workers’ compensation; distinguir custo patronal de contribuição legal do trabalhador. |
| 2 — U.S. Department of Labor, paid leave | https://www.dol.gov/agencies/wb/featured-paid-leave | Inventário oficial dos programas estaduais de licença familiar/médica remunerada e financiamento, com referência temporal de 2026. Verificar se TX/FL têm programas com contribuição obrigatória do empregado. Ausência numa página incompleta ou sem data não basta: fornecer, nesse caso, publicação oficial atualizada ou confirmação dos organismos estaduais. |
| 3 — Florida Statutes 2026, §443.041 | https://www.flsenate.gov/Laws/Statutes/2026/443.041 | Reconfirmar o texto completo anteriormente revisto: não transferir para empregados as contribuições patronais de reemployment. O zero desta parcela já existe; não é evidência de zero em todas as contribuições. |

O primeiro envio útil é o grupo de prioridade 1; para ativar o total, também são necessárias as regras de prioridade 2 e a delimitação completa da cobertura laboral. A legislação geral tem de ser lida em conjunto: uma permissão de desconto salarial não cria, por si, uma obrigação de contribuição.

## Fontes de apoio e referências completas

| Documento oficial | URL | Utilidade e limite |
|---|---|---|
| Texas Constitution, artigo VIII §24-a | https://tlc.texas.gov/docs/legref/TxConst.pdf | Reobter o texto integral que sustenta o zero estadual já revisto. Não prova, isoladamente, todas as componentes locais ou contribuições. |
| Texas Labor Code, capítulo 61 | https://statutes.capitol.texas.gov/Docs/LA/htm/LA.61.htm | Payday Law: distinguir retenções legalmente exigidas, autorização do trabalhador e ordens judiciais. Autorizar um desconto não o torna um imposto nem demonstra que seja facultativo em qualquer contrato. |
| DOL, Comparison of State Unemployment Insurance Laws 2026 — Financing | https://oui.doleta.gov/unemploy/comparison/2026/financing.pdf | Corroboração oficial das contribuições estaduais patronais/do empregado. O URL anual é um localizador candidato, não um download confirmado. Se não existir, obter a edição 2026 através de https://oui.doleta.gov/unemploy/comparison.asp, com capítulo Financing e data. Não substituir por 2025 sem verificar a vigência. |
| DOL/EBSA, Retirement Plans and ERISA FAQ | https://www.dol.gov/agencies/ebsa/about-ebsa/our-activities/resource-center/faqs/retirement-plans-and-erisa | Distinguir benefícios/planos de emprego privado de imposto/contribuição pública; não prova ausência de todos os regimes ou de contribuições contratuais. Não substituir análise da situação de emprego. |
| SSA, COLA factsheet 2026 | https://www.ssa.gov/news/press/factsheets/colafacts2026.pdf | Confirmar diretamente a base máxima e a taxa Social Security 2026; a Publication 15 já corrobora os parâmetros, pelo que este documento não substitui as lacunas estaduais/locais. |
| IRS, Publication 15 (2026) | https://www.irs.gov/publications/p15 | Texto integral das taxas/bases FICA e do financiamento patronal FUTA; separar contribuições patronais das que reduzem líquido do empregado. |
| IRS, Publication 505 (2026) e Rev. Proc. 2025-32 | https://www.irs.gov/publications/p505 e https://www.irs.gov/irb/2025-45_IRB | Worksheets de estimativa anual e parâmetros publicados. Fornecer as páginas anuais completas para rever casos independentes de estimativa, incluindo AMT e créditos; não usar tabelas mensais de retenção como liquidação anual. |
| IRS, Form 6251 instructions | https://www.irs.gov/instructions/i6251 | Confirmar o ano impresso no documento e as regras AMT aplicáveis. O documento anteriormente adquirido era de 2025 e sustenta apenas estrutura; não importar os seus limites anuais. |

Se a revisão destes textos revelar uma autorização local excecional, será necessário recolher localidade de residência/trabalho e a respetiva fonte oficial municipal/condado. Não há ainda fundamento para escolher uma cidade e afirmar que ela representa todo o estado.

Os corpos brutos adquiridos nas fases anteriores não foram localizados nesta instância. Os hashes e a revisão limitada persistem no repositório; não afirmamos ter recalculado os hashes de documentos indisponíveis. Documentos fornecidos serão guardados fora de Git; calcular SHA-256, registar proveniência e validar conteúdo/vigência antes de aceitar regras. Só evidência compacta sem dados privados deverá acompanhar a PR.

## Obrigações legais versus descontos facultativos

| Categoria | Tratamento no cenário |
|---|---|
| Imposto federal, AMT e employee FICA/Additional Medicare | Componentes legais federais modeladas com factos explícitos. Continuam a ser estimativas anuais, não retenções por recibo. |
| Imposto estadual sobre salário | Zero TX/FL no âmbito dos parâmetros anteriormente revistos; sem promoção a cobertura completa. |
| Imposto local sobre salário | Desconhecido até confirmação da competência/proibição local. Nunca inferir zero a partir do estado. |
| Unemployment/reemployment | FL: zero do empregado no parâmetro legal revisto; TX: ainda desconhecido. Os impostos patronais não devem ser subtraídos ao empregado. |
| Workers’ compensation, licença médica/familiar e seguro obrigatório | Atribuição legal e cobertura ainda por confirmar para o cenário privado. Não chamar facultativo nem preencher zero antes da revisão. |
| Plano de saúde, 401(k), seguro ou benefícios escolhidos | Excluídos da estimativa fiscal; não declarar que custam zero. Deduções pré-imposto que alterem bases saem do cenário de bases iguais. Adesão automática com opção de saída não equivale a imposto legal universal. |
| Contribuições de pensão pública/ocupacional obrigatórias | Não são facultativas. Excluídas pela delimitação a emprego privado ordinário; emprego elegível nesses regimes terá de continuar parcial. |
| Quotas contratuais, garnishment, manutenção/ordens judiciais | Podem ser obrigatórias na situação individual sem serem imposto/contribuição universal. Fora do cenário e do conceito de líquido fiscal; não anunciar saldo bancário ou recibo líquido efetivo. |

A intenção é calcular um **benchmark de líquido fiscal anual**, antes de benefícios voluntários e outros descontos individuais explicitamente excluídos. Não é promessa de salário efetivamente pago. Um contributo que seja legalmente obrigatório no cenário não pode ser excluído por mera confirmação genérica.

## Critérios para ativar `net_income`

1. Rever o conjunto oficial acima e confirmar a vigência em 2026 de todas as parcelas relevantes; justificar separadamente qualquer zero local ou contributivo. Um checksum identifica bytes, não valida uma regra.
2. Introduzir confirmação explícita e validada do âmbito privado e da residência/trabalho, distinguindo-a da confirmação federal existente. Recusar ou manter parcial quando faltar algum facto ou houver regime especial.
3. Rever créditos, exclusões, AMT e arredondamento para uma estimativa anual explicitamente limitada; não afirmar uma declaração fiscal final ou total de retenções salariais.
4. Obter casos independentes completos com metodologia/evidência rastreável para ambos os estados, incluindo rendimentos baixos no intervalo, escalões, teto Social Security e limite Additional Medicare. Casos calculados só pelo próprio motor não são referências independentes. Enquanto as fontes locais/contributivas não existirem, o saldo federal é apenas um subtotal, não um caso completo validado.
5. Testar líquido, factos ausentes/especiais, erros, fronteiras e paridade ASGI/WSGI; rever metadados de cobertura. Só então permitir `benchmark_estimate`, nunca ativação por nome do cenário, hashes, carregamento de documentos ou seleção de estado.

Não se ampliam NY/CA/PA nesta continuação. Não há migração ou pacote de BD, publicação, merge ou deployment.
