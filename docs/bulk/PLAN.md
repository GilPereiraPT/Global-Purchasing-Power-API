# Plano de descoberta e importação — Fase 4

Base: branch main mais recente, catálogo de 14 países/40 profissões, inventário
`app/data_inventory.py`, snapshots em `data/` e importadores/Data Manager existentes.
A PR fiscal #13 é independente. Este plano antecede a implementação dos conectores.

1. **Inventário local, leitura apenas**: 560 pares país/profissão, horizonte explícito
   2015–2025, períodos originais, regiões observadas, medidas/unidades, códigos,
   grupos, hashes dos snapshots e erros de refresh. Não confundir snapshots com
   dados importados, nem caches de desenvolvimento com produção. Uma lacuna não
   prova inexistência da estatística na fonte. Inventário de produção requer uma
   exportação autorizada do inventário existente, não acesso à base em produção.
2. **Infraestrutura offline**: downloads limitados/streaming, cache condicional,
   retries transitórios, logs e checksums, SQLite por lotes, retomada por ficheiro
   e ponto de importação, versões preservadas e quarentena de revisões suspeitas.
   Sem importação pesada no ciclo de pedidos da API ou alteração do token.
3. **Banco Mundial**: primeiro conector; uma consulta reúne os 14 países e histórico
   completo de cada indicador existente, com paginação verificável. Maior alcance
   potencial económico/PPP; não publica salários nem calcula poder de compra líquido.
4. **Eurostat TSV gzip**: segundo conector; datasets completos dos indicadores já
   selecionados, dimensões/filtros estritos e histórico. As referências estatísticas
   de rendimento líquido não são resultados do motor fiscal português.
5. **ILOSTAT/BLS/Job Bank/INE-GEP/ONS/INSEE/CBS**: ampliar importadores existentes após
   validar catálogo/licença/versões e mapeamentos. Não fazer pedidos por profissão
   se o dataset completo estiver disponível. Priorizar lacunas concretas do inventário.
6. **OECD/RAIS/IBGE/FSO/Istat/CSO/MoSPI/PBS/BA**: primeiro validar dataflow, layout,
   precisão e acesso. Dados de grandes grupos permanecem separados. Derivados RAIS
   e PLFS existentes não equivalem a nova aquisição oficial. Nunca substituir
   profissões ausentes por grupos ou inferir correspondências só pelo título.

O registo legível por máquina é `app/bulk_catalogue.py`, reproduzido no relatório.
Inclui formatos, história, geografia, classificação, frequência e condições que
precisam de confirmação. As estimativas de novas observações permanecem desconhecidas
até um download válido e a diferença com a base. Não inventar totais ou afirmar
que uma fonte não existe quando ainda não foi verificada.

Atualizações: câmbios diários; indicadores mensais de acordo com a publicação;
verificação mensal de datasets anuais; salários mensal/trimestral. O novo worker
será CLI, isolado e limitado, sem ativar cron ou Actions de produção. ETag,
Last-Modified, hashes e revisão de dados antigos permitem atualizações incrementais.
Agendamento e promoção de artefactos revistos podem depois usar a arquitetura
existente de Actions/Data Manager, preservando as salvaguardas de backup/autorização.
