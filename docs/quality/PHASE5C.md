# Fase 5C — investigação das 19 lacunas económicas

## Decisão e âmbito

Primeira entrega de investigação para a Issue #20, baseada em `main` 29f67d7 (versão instalada 0.5.20 declarada pelo operador). Em 2026-10-03 UTC foram consultadas individualmente as 19 séries WDI e os portais oficiais indicados na Issue. **Nenhuma observação alternativa está aprovada para integração: 0 Exact, 0 Alternative, 19 Unavailable por impossibilidade de verificar valores na fonte candidata, 0 Not comparable confirmados.** Esta classificação é operacional e provisória: não significa que os dados não existam. A decisão fundamentada para cada célula é conservar indisponível até obter o ficheiro, definição, flags e licença. A investigação empírica das fontes alternativas fica bloqueada, não se declara concluída nem recuperação de cobertura.

O Gini da Índia está resolvido segundo o operador (8 observações, última de 2022): não foi consultado, importado nem preparado novamente. A referência 387/406 combinações é fornecida pelo operador, não confirmada por um novo inventário integral nesta sessão. A previsão após esta entrega continua 387/406, sujeita à confirmação. Nenhuma base de produção foi acedida.

## Resultado individual

Todas as respostas WDI foram HTTP 200, sourceid 2, uma página completa, país ISO2/ISO3 e código exactos, anos sem duplicação, valores exclusivamente nulos. Foram revalidados os SHA-256 dos corpos. O `lastupdated` da fonte é 2026-07-13; não é o período de uma observação. O intervalo e a continuidade dos anos consultados constam do JSON, não são anos com valores publicados.

| País | Indicador WDI | Candidata | Resultado WDI | Valor/ano alternativo verificado | Decisão |
|---|---|---|---|---|---|
| DE (DEU) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| FR (FRA) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| GB (GBR) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| NL (NLD) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| CH (CHE) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| IE (IRL) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| US (USA) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| CA (CAN) | `adult_literacy` / `SE.ADT.LITR.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| PT (PRT) | `battle_related_deaths` / `VC.BTL.DETH` | UCDP | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| BR (BRA) | `battle_related_deaths` / `VC.BTL.DETH` | UCDP | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| CH (CHE) | `battle_related_deaths` / `VC.BTL.DETH` | UCDP | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| IE (IRL) | `battle_related_deaths` / `VC.BTL.DETH` | UCDP | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| CA (CAN) | `battle_related_deaths` / `VC.BTL.DETH` | UCDP | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| FR (FRA) | `primary_completion` / `SE.PRM.CMPT.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| BR (BRA) | `primary_completion` / `SE.PRM.CMPT.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| NL (NLD) | `primary_completion` / `SE.PRM.CMPT.ZS` | UIS | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| PK (PAK) | `safe_sanitation` / `SH.STA.SMSS.ZS` | JMP | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| PK (PAK) | `intentional_homicides_female` / `VC.IHR.PSRC.FE.P5` | UNODC | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |
| PK (PAK) | `intentional_homicides_male` / `VC.IHR.PSRC.MA.P5` | UNODC | 66 anos consultados; 0 valores não nulos | — | Unavailable: acesso à alternativa bloqueado |

URLs WDI exactas, timestamp UTC, checksum, unidade, anos e definição oficial por código estão em [phase5c-evidence.json](phase5c-evidence.json). Corpos de investigação ficaram no workspace privado, fora do Git. Os checksums WDI são de respostas obtidas, nunca de datasets alternativos não descarregados. Falhas `ProxyError` não têm corpo/dataset/SHA-256 inventado.

## Matriz de equivalência metodológica e licenças

As definições abaixo foram verificadas através do endpoint oficial World Bank `/v2/indicator/{code}?format=json`, seleccionando a entrada WDI source 2. Ser o produtor original não demonstra equivalência de todas as séries do seu catálogo.

| Grupo | Definição WDI verificada e critério de Exact | Excluir ou apresentar independentemente | Licença/atribuição e estado |
|---|---|---|---|
| A, 8 países — UIS | População nacional total de 15+ que consegue ler **e** escrever com compreensão uma frase simples do quotidiano; percentagem; mesmo ano, idade, sexo total, método/flags e universo. | PIAAC, proficiência funcional, escalões etários distintos ou escolaridade não substituem esta taxa. Sem dataset não se atribui Not comparable a uma série concreta. | Licença específica do bulk/API UIS não obtida. A página geral UNESCO de acesso aberto também foi bloqueada; não presumir CC BY ou direitos de redistribuição de cada série. Atribuir UIS, dataset/código, edição, ano e URL após validação. |
| B, 5 países — UCDP | Mortes militares e civis directamente relacionadas com combate entre partes da díade; número de pessoas nacional/ano. Validar universo de conflitos, estimativa usada, regra de agregação e localização efectiva dos eventos contra WDI. | País participante não é país onde ocorreram mortes. Ausência de linha não é zero; não somar estimates low/best/high nem incluir mortes unilaterais/violência não estatal sem equivalência. | A Issue indica v26.1, gratuito, CC BY 4.0; é informação documentada pelo operador, não confirmação independente nesta sessão. Obter codebook e licença exactos; atribuição/citação/autores/versão e transformações antes de redistribuir. |
| C, 3 países — UIS | **Gross intake ratio to the last grade of primary education**: novos entrantes (matrículas menos repetentes) no último ano, independentemente da idade, divididos pela população com idade de entrada nesse ano. WDI não ajusta os desistentes nesse último ano. Percentagem, total nacional, ISCED/idade oficiais. Pode exceder 100%; não aplicar limite genérico 100. | Taxa estimada SDG 4.1.2 de conclusão ou escolaridade atingida não é automaticamente este rácio. Só uma série identificada e validada pode ser Alternative com ID independente. | Como A. Metadados WDI indicam bulk CSV UIS publicado 2026-02, consultado pelo WB 2026-03-19; não prova presença de FR/BR/NL nem licença do ficheiro. |
| D, PK — JMP | Percentagem da população nacional com instalação melhorada não partilhada e excreta eliminados com segurança in situ ou transportados e tratados fora; população total, ano e flags/estimativa publicados. | Serviços básicos, apenas acesso a sanita/rede, componentes de tratamento isolados ou urbano/rural não equivalem ao total nacional safely managed. Sem total publicado não derivar de componentes. | Licença JMP e eventuais excepções de terceiros não obtidas. A página legal UNICEF também bloqueada. Atribuir WHO/UNICEF JMP, edição e URL após confirmar termos específicos. Metadados WDI indicam publicação 2025-08-25, não download nosso. |
| E, PK, feminino/masculino — UNODC | Morte ilícita infligida com intenção de matar ou causar lesão grave; vítimas nacionais, sexo feminino/masculino, taxa respectivamente por 100 000 mulheres/homens, ano comum ao denominador e definição ICCS 0101 confirmada. | Número absoluto, taxa com população total no denominador, autores do crime, feminicídio ou mortes em conflito não substituem a série. Não repartir taxa total por percentagens. | Licença específica UNODC/terceiros não obtida. Atribuir UNODC, dataset/código ICCS, edição e fontes nacionais/flags após confirmação dos termos. |

Não existe equivalência Exact confirmada nem autorização de redistribuição de uma alternativa. Não foram observados valores oficiais concretos das alternativas: os campos valor/ano ficam vazios, não zero.

## Acesso, downloads e aquisição alternativa pelo operador

Os GET às páginas oficiais devolvem `ProxyError` antes de obter resposta HTTP: UIS resources/bulk/resources e documentação `https://api.uis.unesco.org/api/public/documentation/`; JMP countries/pakistan e data/downloads; UNODC datasearch; UCDP downloads/apidocs. Os pedidos de descoberta à API UCDP e possíveis caminhos CSV também foram bloqueados; esses caminhos não são contratos de download validados. Não foi tentado contornar o proxy, desligar TLS nem obter dados de mirrors não oficiais.

1. Num navegador/rede autorizada, abrir exclusivamente os portais: [UIS bulk](https://databrowser.uis.unesco.org/resources/bulk), [UIS API](https://api.uis.unesco.org/api/public/documentation/), [JMP Paquistão](https://washdata.org/countries/pakistan), [JMP downloads](https://washdata.org/data/downloads), [UNODC pesquisa](https://data.unodc.org/datasearch), [UCDP downloads](https://ucdp.uu.se/downloads/).
2. UIS: obter bulk educação SDG4/OPRI, dicionário de códigos, flags e nota metodológica. Seleccionar os oito países para alfabetização 15+ e FR/BR/NL para o rácio bruto exacto, preservando também linhas nulas/suprimidas e código oficial. Não escolher pelo título traduzido apenas. Obter licença específica e versão.
3. UCDP: obter Battle-Related Deaths v26.1 (ou edição identificada pelo portal), codebook, country/location mapping e licença. Não escolher ficheiro apenas por um URL previsível. Guardar as cinco selecções e evidência de cobertura do universo; uma selecção vazia não autoriza zero.
4. JMP: descarregar workbook nacional do PK ou bulk nacional, notas/flags/edição e licença; inspeccionar a série total nacional safely managed sanitation. Conservar workbook original e nomes de folha/célula. Não substituir por basic sanitation.
5. UNODC: exportar Victims of intentional homicide, Paquistão, sexo feminino e masculino, medida rate com denominadores por sexo; incluir dicionário, anos, flags, metodologia e licença. Não converter contagens por estimativa populacional própria.
6. Guardar ficheiros originais numa pasta privada fora do repositório/public_html e das bases activas. Para cada artefacto criar manifesto com URL exacto e URL final de download, timestamp UTC, nome, tamanho, SHA-256 (`sha256sum ficheiro`), versão, país/código, filtros, definição/unidade, flags, licença/URL/atribuição e eventual selecção manual. Não incluir cookies, tokens nem URLs assinados privados no relatório público. Não desactivar verificação TLS. Upload do original, codebook e licença permite continuar esta análise; exemplos incompletos não bastam.
7. Alternativamente, disponibilizar acesso de rede aos hosts oficiais UIS/JMP/UNODC/UCDP e aos destinos reais dos downloads, depois de os confirmar. Não substituir a allowlist desconhecida do ambiente nem acrescentar hosts guessed. Os bloqueios desta sessão são do proxy de rede, não uma rejeição de aprovação automática.

## Infraestrutura existente e plano mínimo de implementação

- `app/bulk_core.py`: Downloader com limites de tamanho, TLS, host/redirect permitido, checksums e artefactos; BulkStore separado com chave de observação, versões, checkpoints, quarentena e proveniência. Reutilizar após confirmar hosts/contratos; actualmente só aceita hosts dos produtores já registados, por isso não basta apontar a outro URL. Não alargar HOSTS preventivamente nem fingir que URI WDI identifica um ficheiro UIS/UCDP/JMP/UNODC.
- `app/bulk_world_bank.py` e `scripts/bulk_acquire.py`: parser/worker WDI source 2 verificado; não servem de parser alternativo sem adaptação validada. Mantêm null como missing. Nenhum run de aquisição/importação foi executado nesta entrega.
- `app/country_insights_store.py`: PK `(country, indicator, year)`, sem fonte na identidade; a resposta atribui World Bank. **Não suporta misturar fonte alternativa no mesmo ID sem perder proveniência.** Adaptador de staging sozinho não torna a publicação compatível. Séries não equivalentes precisam de ID independente, metadados/atribuição e desenho explícito de leitura/publicação revisto, preservando contratos.
- Data Manager económico actual selecciona `world_bank`/`eurostat`. `app/bulk_publication.py` e os uploads bulk-preview/publish são exclusivos de salários e aceitam schema salarial, não pacote económico. Não reutilizar este schema, botão ou projecção para publicar economia. Backups/autorizações existentes são úteis, mas a futura transferência económica necessita de compatibilidade e testes próprios.

Após aquisição completa: (1) revisão de equivalência/licença por série; (2) adaptador mínimo da fonte efectivamente aprovada, conservando fonte/dataset/classificação/metodologia/flags e artefacto; (3) ingestão através de BulkStore num workspace isolado; (4) testes com amostras autênticas de país, denominador, método, null/suppression, truncagem/checksum, versões e duplicados; (5) revisão de projecção/atribuição no modelo económico e comparação com novo inventário; (6) proposta de publicação autorizada e rollback, em PR própria se houver alterações de produção. Não construir parsers de layouts desconhecidos a partir de fixtures inventadas.

## Proposta de publicação controlada

**Lista exacta de dados integráveis nesta entrega: vazia.** Não existe pacote nem observação aceite; não foi criada staging.sqlite3 vazia para aparentar aquisição. Arquivos de evidência WDI/metadados não são dados de publicação. Não reimportar Gini IN. Não executar refresh global para repetir 19 respostas nulas.

Antes de futura publicação: obter inventário económico actualizado autorizado e logs apenas necessários; comparar fonte/indicador/país/ano/unidade/dimensões/metodologia; excluir duplicados/revisões não aprovadas; manter backup com ensaio de recuperação e espaço/permissões; apresentar lista e checksums do lote e obter revisão/autorização explícita. Não usar o mecanismo salarial para esse lote. Nenhuma agenda foi activada e nenhuma alteração de produção está proposta nesta PR.

## Verificação

19 respostas WDI completas com país/código/sourceid/anos e hashes verificados; 6 metadados de definição oficiais verificados; tentativas alternativas bloqueadas documentadas. Suite completa (`.venv/bin/python -m pytest -q`): **640 testes aprovados, 0 falhas**, 85,59 s; 1 aviso de depreciação herdado do Starlette. Testes de adaptador/ingestão alternativa não existem porque nenhuma fonte/layout foi validado. Isto não é uma aquisição live alternativa nem validação sintética de novos dados.
