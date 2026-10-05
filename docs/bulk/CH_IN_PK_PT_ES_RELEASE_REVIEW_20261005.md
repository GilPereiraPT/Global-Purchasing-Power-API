# Revisão salarial CH / IN / PK / PT / ES — 5 de outubro de 2026

## Resultado preparado para revisão

| País | Antes desta continuação | Alteração preparada | Precisão |
|---|---|---|---|
| CH | Cubo BFS privado; snapshot runtime ausente | Snapshot publicável com 10 640 células: 10 020 aceites, 430 incertas, 190 suprimidas; 38 grupos, sete anos bienais 2012–2024, oito geografias | Contexto CH-ISCO-19 de dois dígitos; as 40 profissões da interface têm contexto nacional mediano de 2024, não salários exatos |
| PT | Escalas públicas e contexto ILOSTAT; sem snapshot exato CPP | 10 observações nacionais de 2024: nove grandes grupos CPP e total, indicador INE 0012655 | Ganho médio mensal, EUR, universo Quadros de Pessoal; não salário exato nem remuneração anual com 14 pagamentos |
| PK | Contexto ILOSTAT existente | 120 células PBS: nove grandes grupos e total × dois períodos × três sexos × média/mediana | Salário mensal declarado na tabela; PKR; bruto/líquido não especificado, não inferido |
| ES | EAES 28186 já publicada no código: 918 células 2008–2024 | Nova aquisição oficial coincide integralmente com o snapshot existente; sem duplicação | Grandes grupos CNO-11; salários brutos anuais |
| IN | Snapshot derivado PLFS 2025 com 597 registos, explicitamente de fonte secundária | Exportação oficial rural com 117 216 linhas / 234 432 células adquirida e auditada, exclusivamente em staging privado | Taxas diárias rurais por categoria, sexo, Estado e All India; sem ativação |

**Zero novos salários de profissões exatas.** Os novos contextos PT/PK não entram em `national_occupation_wage`, nas comparações salariais exatas ou nas contagens de pares exatos. A fiscalidade dos EUA continua suspensa. Não houve acesso à produção, merge ou deployment.

## Suíça: reutilização fundamentada e workflow corrigido

A comunicação oficial de 5 de junho de 2026 descreve a abolição da autorização e compensação por utilização comercial de resultados estatísticos federais, permitindo reutilização e redistribuição com atribuição. A revisão entrou em vigor em 15 de julho de 2026:

https://www.geo.admin.ch/de/newnsb/f1zWSNpVPekdwKPMGT9dd

A aplicação à presente tabela é uma conclusão desta revisão: trata-se de uma tabela pública de resultados estatísticos agregados do BFS, sem microdados nem material de terceiros identificado. A prova foi lida através da pesquisa web; o pedido HTTP direto ao mesmo URL devolveu 502. Não existe corpo HTML original dessa comunicação no pacote de originais; não se confunde a extração web com aquisição dos bytes originais.

O corpo estatístico recuperado tem 66 715 bytes e SHA-256 `1188ba467a970ae19cfcb7dcbc1c99b14624aeaf2de5a5f6b4ec4adf6dba6301`, coincidindo com o corpo da aquisição anterior. Metadados e query desta aquisição têm checksums próprios no snapshot. Atribuição ao FSO/ESS e referência da tabela constam do snapshot e das respostas de contexto.

`scripts/ch_bfs_snapshot.py` usa os códigos franceses efetivamente publicados, todos os anos e regiões revistos, e totais explícitos de idade/sexo. Valida bytes, query e cubo através do importador revisto na PR #42. O workflow herdado foi substituído por esta chamada. Não há escolha silenciosa da primeira categoria nem promoção de células incertas a valores aceites. Futuras dimensões/anos inesperados exigem revisão.

## Portugal e Paquistão

PT: o indicador anterior 0010385 usa NUTS 2013 e termina em 2022. A nova aquisição usa 0012655, NUTS 2024, com referência 2024. O catálogo oficial dados.gov.pt identifica CC BY 4.0:

https://dados.gov.pt/pt/datasets/687052028c1cd0da86631ab2/

O pedido nacional foi adquirido; metadados do indicador novo devolveram 429, a publicação GEP devolveu 502 e o pedido de 2023 devolveu 502. Não se reivindica cobertura histórica/regional nova nem categorias CPP de quatro dígitos. O título e os rótulos oficiais foram preservados.

PK: extração da tabela 5.4, página impressa 74, do relatório LFS 2024–25. As seis colunas e dois períodos foram separados, conservando os rótulos originais, incluindo `Mangers`. Os identificadores textuais da API são internos; não são apresentados como códigos PSCO publicados na tabela.

https://www.pbs.gov.pk/wp-content/uploads/2020/07/LFS-2024-25-Annual-Report.pdf

A página de disseminação publicada do PBS permite reutilizar agregados Tier 1 com atribuição. O PDF de política de 2026 encontrado em pesquisa tem título de consultation draft: não é usado como prova de norma promulgada. A base desta publicação é a página operacional de disseminação, cuja aquisição original foi preservada:

https://www.pbs.gov.pk/data-dissemination/

`scripts/official_group_snapshot.py` reproduz os valores a partir dos originais. Novos anos, rótulos ou estrutura da tabela são recusados até revisão. Não se agregam médias ou medianas de grupos para calcular salários nacionais.

## Índia: dados recuperados, dois bloqueios concretos

A exportação CSV completa do Labour Bureau contém 117 216 linhas; o HTML mostra apenas 5 000 e indica explicitamente esse limite. A auditoria usa o CSV completo, não a amostra visível.

https://www.labourbureau.gov.in/home/excel_download_ruralWage_data?state_id=1

Foram observadas 116 712 identidades únicas e 504 linhas duplicadas, das quais 92 identidades têm valores divergentes. As 234 432 células originais incluem 114 313 números positivos, 74 258 marcadores `-`, 43 110 marcadores `@` e 2 751 campos vazios. `@` significa menos de cinco cotações; `-` indica operação/categoria indisponível; nenhum representa salário zero. Os originais e todas as alternativas duplicadas foram conservados.

Os dados atravessam 29 anos de inquérito, 35 rótulos geográficos incluindo All India e 40 rótulos profissionais históricos. Isto não significa 40 profissões atuais nem cobertura uniforme: a metodologia atual descreve 25 categorias e uma alteração amostral desde julho de 2025. O período fiscal e o mês mantêm os rótulos originais, sem datas reconstruídas.

As duas páginas oficiais divergem: `termsandconditions` permite reprodução gratuita com atribuição; `websitepolicy` exige autorização prévia. A publicação está pendente de esclarecimento sobre a regra aplicável, além da resolução das identidades conflituantes:

https://www.labourbureau.gov.in/termsandconditions

https://www.labourbureau.gov.in/websitepolicy

`scripts/in_rural_staging.py` gera uma auditoria sem valores salariais e staging privado fora de `data/`. Não há importador runtime deste staging. Não se transformam taxas rurais diárias em salários mensais de mercado. As fontes, qualidade e limitações são preservadas em `in-rural-source-audit-20261005.json`.

Também foram adquiridos o layout e README oficiais PLFS 2025. O layout CPERV1 confirma `ocu_cws` com três posições; o acesso aos microdados requer login. O README adverte contra estudos de variáveis para além dos indicadores de emprego/desemprego. Não foram adquiridos microdados pessoais, revalidado o snapshot derivado anterior ou acrescentados salários PLFS nesta continuação.

## Verificação sem terminal após futura integração autorizada

1. Rever esta PR, os testes e o CI. Ainda não fazer publicação de dados através do Data Manager.
2. Após merge autorizado, utilizar o procedimento habitual de **Atualizar API** e reinício Passenger no cPanel. Os três novos snapshots são ficheiros runtime distribuídos com o código; não exigem migração SQL.
3. Abrir `/v1/data-inventory`: verificar CH com 10 640 células / 10 020 aceites, PT com 10 observações e PK com 120. Confirmar a presença dos três snapshots no inventário.
4. Abrir `/v1/pt/earnings/groups/2?period=2024`: ganho médio mensal 2 395,88 EUR, claramente identificado como grupo.
5. Abrir `/v1/pk/earnings/groups/professionals?sex=women&period=2024-25`: média 50 660 e mediana 53 900 PKR/mês, sem indicação inventada de bruto/líquido.
6. Abrir `/v1/earnwage/overview?country=CH&occupation=nurse`: contexto suíço disponível; salário exato não passa a disponível por causa desse contexto.
7. Confirmar que o staging rural indiano permanece fora dos ficheiros runtime. Não o carregar no Data Manager nem em caminhos públicos.

Os snapshots CH/PT/PK estão preparados para revisão; a cobertura de produção só pode ser afirmada após atualização e verificação dos endpoints. IE e os salários dos restantes países foram preservados.

## Validação local

Suite completa: **1 039 testes aprovados, zero falhas e 20 subtestes aprovados**. Inclui qualidade do cubo CH, rejeição de valores inválidos, isolamento dos contextos, paridade ASGI/WSGI, conflitos/flags do CSV rural e reprodução dos valores PT/PK a partir dos originais. Mantém-se um aviso herdado de depreciação Starlette/httpx.

Após a suite completa, acrescentou-se tratamento explícito para snapshots opcionais ausentes, sem erro 500 no inventário: **14 testes dirigidos aprovados**. O arquivo runtime real foi validado em instalação isolada, incluindo Passenger WSGI CH/PT/PK e exclusão do staging IN.
