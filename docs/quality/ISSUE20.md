# #20 — análise das 20 lacunas WDI

## Resultado

**Uma lacuna com valores oficiais e staging aceite: Gini da Índia.** O endpoint WDI devolve oito observações, a mais recente 2022 = 25,5. O staging Phase 4 final contém as mesmas oito observações aceites, sem razões de quarentena. A ausência foi reportada no inventário de produção da tarefa; não foi acedida a base nem fornecido aqui o export integral com logs. Por isso confirma-se a discrepância staging/inventário reportado, não se prova a causa exacta de importação/transferência/leitura.

**As outras 19 células não têm qualquer valor não nulo na resposta WDI actual.** HTTP200, dimensões de país/indicador verificadas, todas as páginas incluídas. Isto não demonstra inexistência em todas as fontes ou para sempre. Não confundir resposta vazia/nula com falha HTTP, zeros, validade actual ou publicação histórica noutra edição. Quatro primeiras consultas de alfabetização falharam; retry sequencial limitado confirmou respostas válidas sem valores, sem esconder as primeiras falhas.

Consulta independente em 3 de Outubro de 2026 (Europe/Lisbon); os metadados WDI reportam lastupdated 2026-07-13. A data do refresh da fonte não é o ano da observação. 25,5 é Gini de 2022, nunca um valor estimado de 2026. Não foram importados dados.

## Evidência por célula

| País | Indicador/código | Resultado WDI | Ano/valor mais recente | Staging final | Fonte candidata alternativa |
|---|---|---|---|---|---|
| DE | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| FR | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| GB | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| NL | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| CH | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| IE | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| US | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| CA | adult_literacy / SE.ADT.LITR.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| PT | battle_related_deaths / VC.BTL.DETH | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://ucdp.uu.se/downloads/) |
| BR | battle_related_deaths / VC.BTL.DETH | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://ucdp.uu.se/downloads/) |
| CH | battle_related_deaths / VC.BTL.DETH | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://ucdp.uu.se/downloads/) |
| IE | battle_related_deaths / VC.BTL.DETH | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://ucdp.uu.se/downloads/) |
| CA | battle_related_deaths / VC.BTL.DETH | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://ucdp.uu.se/downloads/) |
| FR | primary_completion / SE.PRM.CMPT.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| BR | primary_completion / SE.PRM.CMPT.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| NL | primary_completion / SE.PRM.CMPT.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://databrowser.uis.unesco.org/) |
| IN | gini / SI.POV.GINI | 8 valores disponíveis | 2022 / 25.5 | 8 (accepted) | [portal candidato](https://pip.worldbank.org/) |
| PK | safe_sanitation / SH.STA.SMSS.ZS | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://washdata.org/data/household) |
| PK | intentional_homicides_female / VC.IHR.PSRC.FE.P5 | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://dataunodc.un.org/) |
| PK | intentional_homicides_male / VC.IHR.PSRC.MA.P5 | 0 valores não nulos | indisponível, não zero | 0 () | [portal candidato](https://dataunodc.un.org/) |

O índice JSON acompanhante conserva URLs exactas, unidade, timestamp de consulta, SHA-256 da resposta, número de páginas e estado de staging de cada combinação. Corpos grandes não são incluídos no Git; os requests GET oficiais são reproduzíveis pelas URLs. Nenhum path/credencial/configuração de produção é incluído.

## Definições, alternativas e licenças

- Alfabetização adulta (8 países): proporção de pessoas 15+ que conseguem ler/escrever uma frase simples. UNESCO UIS é a fonte candidata; PIAAC/OECD mede proficiência funcional em populações/faixas etárias distintas e não é substituição automática. Não assumir 100% em países desenvolvidos.
- Mortes em combate (5 países): UCDP é fonte de conflitos e fatalities. Não atribuir zero a países ausentes só porque não se reconhece um conflito. Qualquer derivação de zero exigiria cobertura completa e regras explícitas noutro indicador; não preencher WDI por inferência.
- Conclusão primária (3 países): verificar UIS directamente, ano, denominador e se é rácio bruto/taxa de conclusão estimada. Nível educacional atingido por adultos ou frequência escolar não substituem a definição WDI.
- Saneamento seguro PK: WHO/UNICEF JMP é fonte candidata. Serviços básicos não equivalem a serviços geridos com segurança; ausência de dados sobre tratamento não permite estimar a cadeia completa.
- Homicídios femininos/masculinos PK: UNODC é fonte candidata. Validar vítimas por sexo, ano e população feminina/masculina no denominador; não repartir um total de homicídios por percentagens ou copiar a taxa total.
- Gini IN: manter a definição WDI/Poverty and Inequality Platform, ano e tipo de distribuição. Uma nova edição/metodologia não deve ser misturada silenciosamente com outra série.

O acesso directo aos portais UIS/UCDP/JMP/UNODC e à página de termos World Bank foi recusado pelo proxy de rede (ProxyError). As URLs são candidatas oficiais, não datasets automaticamente aceites. Não foram validadas nesta sessão a equivalência das séries alternativas, a cobertura exacta nem os direitos específicos de redistribuição. Não presumir licença livre por ser entidade pública. A fonte WDI já integrada é reutilizável pelo fluxo existente, mas qualquer substituição nova continua bloqueada até confirmar termos, atribuição e excepções.

## Proposta limitada, sem execução

1. Para IN/gini, operador confirma o estado/histórico e última tentativa no inventário actual. Depois de autorização e backup, utilizar o Data Manager existente: world_bank → IN → gini → missing. É uma célula, com oito linhas históricas oficiais já aceites no staging; validar o preview/source/year/limites e preservar dados existentes. Não importar automaticamente nem contornar quarentena.
2. Se o inventário actual já tiver valores, parar; a ausência original pode ser anterior a uma actualização. Rever logs para distinguir falta de transferência, falha de refresh e erro de leitura. Não há aqui acesso ou prova dos logs de produção.
3. Para as 19 restantes, conservar indisponível e registar fonte/última tentativa. Não repetir importações cegas para tentar aumentar a contagem.
4. Próxima investigação de fontes alternativas exige acesso aos domínios oficiais acima, amostras documentadas e validação de definição/licença em PR separada. Priorizar PK/JMP e PK/UNODC; não ligar providers antes dessa validação.

## Validação

20/20 respostas finais HTTP200, país/indicador correctos, páginas completas, hashes revalidados e reconciliação com staging isolado. 19 sem valores, 1 com oito valores oficiais aceites. Nenhuma fonte nula foi convertida em zero. O relatório é a primeira entrega solicitada na tarefa #20; não modifica importadores/API/produção.
