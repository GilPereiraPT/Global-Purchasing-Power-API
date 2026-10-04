# Fontes ainda necessárias — Texas e Florida 2026

Atualizado após leitura dos originais do ZIP fornecido em 4 de outubro de 2026. O [relatório de validação](US_TX_FL_UPLOADED_SOURCES_2026.md) identifica os dez corpos originais, hashes, rejeições e regras incorporadas. **Desemprego e workers’ compensation já têm regras revistas; líquido total continua indisponível.**

## Correção do pedido anterior

O pedido anterior atribuía incorretamente ao Texas Tax Code, capítulo 302, uma proibição de imposto municipal sobre rendimento. O original https://tcss.legis.texas.gov/resources/TX/htm/TX.302.htm trata de property taxes e occupation taxes. **Não é fundamento para zero de imposto salarial local.** A referência anterior foi retirada dos pedidos de prova de proibição; o capítulo permanece apenas no relatório como evidência da correção.

Os capítulos Texas Labor Code 204, 406 e 415 e Florida §440.21 foram fornecidos e revistos. Não é necessário repetir essa aquisição. Também foram recebidos a Constituição da Florida, §166.201 e a página DOL paid leave, mas estes não fecham as lacunas abaixo.

## Documentos para fechar os bloqueios

| Documento / URL oficial | Regra a confirmar e lacuna efetiva |
|---|---|
| Texas: texto/posição oficial abrangente sobre competência e incidência de impostos locais sobre salários em 2026. Localizador legislativo candidato: https://tcss.legis.texas.gov/resources/LG/htm/LG.101.htm | Confirmar eventual proibição/ausência de imposto salarial municipal e de condados, incluindo competência home-rule e alcance a empregados. O capítulo 101 é um localizador a investigar, **não uma regra de proibição já verificada**. Se não contiver a resposta, fornecer a legislação ou orientação oficial pertinente; não usar o capítulo 302 nem listas incompletas de impostos como prova de ausência. |
| Florida: Laws of Florida, capítulo 2026-45 — https://laws.flrules.org/2026/45 | Ler o diploma completo e a data de eficácia da alteração a §166.201/§377.8161, comparando o texto anterior e posterior durante 2026. O HTML de §166.201 mostra a referência à alteração, mas não fornece o ato ou a sua data de eficácia. |
| Florida: fundamento oficial completo da não incidência de imposto local sobre salário do residente, articulado com https://www.flsenate.gov/Laws/Constitution e https://www.flsenate.gov/Laws/Statutes/2026/166.201 | Os documentos já fornecidos limitam competência e tributação, mas não são uma proibição absoluta sem ressalvas: VII.5(a) menciona montantes creditáveis/dedutíveis. Confirmar ausência de autorização local salarial aplicável e necessidade de identificação de município/condado; não concluir zero só por haver zero estadual. |
| DOL: programa/lista de contribuições paid family/medical leave e disability com vigência em 2026; ponto de entrada https://www.dol.gov/agencies/wb/featured-paid-leave | O corpo fornecido inclui interativos e uma secção paid sick leave datada de dezembro de 2024; não contém prova completa e temporal de zero em TX/FL em 2026. Fornecer os dados originais dos interativos/publicação oficial atualizada ou confirmação dos organismos estaduais de que não existe contribuição obrigatória do trabalhador no âmbito definido. |
| Texas/Florida: eventuais regimes de seguro de paid leave voluntário, se usados como fundamento para exclusão. Localizador FL candidato: https://www.flsenate.gov/Laws/Statutes/2026/627.445 | Confirmar no texto original se existe regime, se a adesão/financiamento é facultativa e se alguma lei impõe contribuição salarial. Este URL foi bloqueado e a disposição **não foi validada**; não inferir a regra a partir do número da secção. Seguro facultativo, se confirmado, será uma exclusão explícita do benchmark, não uma obrigação legal omitida. |

As quatro novas consultas constam de `us_tx_fl_uploaded_review_20261004.json`; foram bloqueadas pelo gateway. Não há nova aquisição bem-sucedida nem confirmação de validade dos localizadores candidatos. Quando necessário, fornecer texto oficial municipal/condado e identificar residência/trabalho em vez de afirmar cobertura estadual uniforme.

Enviar PDF ou HTML completo, URL de origem, data de obtenção e versão/vigência aplicável a 2026. Não são necessários credenciais, configuração, documentos pessoais ou dados de produção. Os originais serão guardados fora de Git e comparados com os respetivos hashes; uma extração TXT é auxiliar e não substitui o original. Respostas HTML de página inicial a pedidos de PDF serão rejeitadas mesmo com HTTP 200 e checksum correto.

## Factos e distinção de encargos

O cenário proposto para um futuro líquido é empregado privado ordinário, solteiro, residente fiscal durante todo o ano, sem dependentes, salário de um empregador, trabalho e residência exclusivamente no mesmo estado, sem regime público/ocupacional/ferroviário, outros rendimentos ou deduções especiais. Mantém o intervalo federal 19540–500000 e os factos federais existentes.

A API aceita agora `employment_type` e `workers_compensation_exception_agreement` em `us_facts`. Para zero de workers’ compensation, exige `employment_type="ordinary_private_employee"` e `workers_compensation_exception_agreement=false`. Independent contractor, subcontractor, owner operator, public employee, special regime ou acordo excecional não são cenário líquido suportado. A confirmação federal existente não substitui estes factos. A residência/trabalho exclusivamente no estado ainda não é um facto recolhido/validado pelo modelo; será necessário antes de ativar líquido.

Desemprego/reemployment e prémios workers’ compensation são analisados segundo a atribuição legal ao empregador/trabalhador. Plano de saúde, 401(k) e benefícios facultativos ficam fora do benchmark fiscal, sem declarar custo zero; contribuições públicas/ocupacionais obrigatórias não são facultativas. Quotas contratuais, garnishment e ordens judiciais também não são impostos universais e ficam fora deste cenário explícito. Bases pré-imposto divergentes continuam sem suporte.

Só após completar as fontes locais/paid leave, os factos de incidência, as demais obrigações aplicáveis e referências independentes completas poderá haver `benchmark_estimate` com `net_income`. Hashes, documentos carregados, seleção do estado ou o saldo federal não o ativam automaticamente. Não ampliar NY/CA/PA, importar BD, publicar, fazer merge ou deployment nesta etapa.
