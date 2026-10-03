# Aquisição em massa — Fases 4 e 4B

Esta entrega implementa a infraestrutura offline, Banco Mundial WDI, Eurostat TSV
gzip e a expansão salarial BLS/Job Bank. Ver o [relatório da Fase 4B](PHASE4B.md)
para os resultados mais recentes. Os números seguintes documentam a Fase 4 original. Parte de `main` (`1a57090`), numa branch
independente da PR fiscal #13. Não altera cálculos salariais, Android, token
administrativo ou sistema de deployment.

## Resultado original da Fase 4, em 3 de outubro de 2026

| Fonte | Observações aceites | Em quarentena |
| --- | ---: | ---: |
| Banco Mundial — 29 indicadores | 11 926 | 243 |
| Eurostat — 3 datasets | 3 210 | 14 |
| Total | **15 136** | **257** |

Foram descarregados 32 datasets completos/seleções multipaís, para os 14 países.
O Banco Mundial fornece histórico desde 1960, conforme o indicador. A validação
conservou 14 833 células ausentes/suprimidas como ausentes, sem as transformar em
zero. As 15 393 observações selecionadas não nulas dividem-se nas aceites e em
quarentena. Os períodos, filtros, unidades, flags, edição/data de publicação quando
fornecida, URLs e hashes originais são preservados.

**São observações novas num staging local inicialmente vazio; não foi demonstrado
que todas sejam inéditas relativamente à base de produção.** Não foi fornecida uma
exportação do inventário de produção. A baseline usa o inventário/catálogo e os
snapshots do repositório; não inventa o estado de produção.

**Na Fase 4 original não tinham sido acrescentados salários de profissões individuais.** As 192 observações
aceites de `earn_nt_net` são referências estatísticas nacionais, não salários
profissionais nem resultados do motor fiscal português. Os 7 723 registos dos
snapshots existentes incluem grupos, derivados e várias medidas; 202 pares têm
registos associados após interpretar os códigos SOC originais. Não são contados
como nova aquisição oficial.

A repetição dos 32 imports inseriu **zero novas observações** e conservou as mesmas
15 136 aceites e 257 em quarentena. A exportação local, para uma base SQLite nova,
produziu 11 926 linhas WDI e 3 210 Eurostat compatíveis com os leitores existentes.
A proveniência/histórico de versões acompanha essa base. Não houve escrita em
bases de produção.

## Inventário e relatórios

- [Preparação da primeira publicação — Phase 4E](PHASE4E.md): exportação pelo
  operador, pacote candidato, gates de autorização e procedimento Data Manager.
- [Plano de fontes](PLAN.md): prioridades e tarefas seguintes.
- [Geração de inventários e autorização de exports](INVENTORY_EXPORT.md): os
  dashboards/JSON completos são reproduzíveis e ficam em `docs/bulk/generated/`,
  fora do Git. A matriz mantém 560 pares, períodos, regiões e classificações.
- [Evidência original da Fase 4](acquisition-evidence.json): hashes e contagens.
- [Revisão das 257 versões em quarentena](quarantine-review.csv): todos os casos,
  motivos e categorias de avaliação manual, sem aprovação automática.
- [Resultados da expansão salarial](PHASE4B.md), [BLS](BLS.md) e [Job Bank](JOB_BANK.md).
- [Acesso às fontes](source-access.json): provas de conectividade; uma página
  HTTP 200 não prova que todo o dataset seja acessível ou reutilizável.

A matriz preserva grupos e intervalos plurianuais. Não transforma 2023–2024 em
observações anuais separadas. Quando o universo regional não foi validado, indica
isso explicitamente; as opções regionais configuradas têm lacunas discriminadas.
CH/IT têm fontes auditadas de grupos incompatíveis com profissões individuais;
outros casos sem fonte validada são identificados como desconhecidos, não como
prova de inexistência de uma fonte.

O registo de classificações tem 560 entradas e reutiliza códigos nacionais já
revistos. Mantém NCO indiano como contexto de grupo e rejeita-o para salários
individuais. Rejeita códigos amplos, versões erradas ou correspondências não
validadas; não afirma correspondência universal um-para-um. DE precisa de evidência
KldB original antes de ganhar um novo mapeamento no conector; IDs de páginas não
são códigos profissionais.

## Execução isolada

Usar o Python/dependências existentes; não há pacotes novos.

```sh
.venv/bin/python -m scripts.bulk_inventory --output /workspace/earnwage-inventory
.venv/bin/python -m scripts.bulk_acquire --workspace /workspace/earnwage-bulk \
  --provider world_bank --dataset inflation_annual --dataset ppp_private_consumption --due
.venv/bin/python -m scripts.bulk_acquire --workspace /workspace/earnwage-bulk \
  --provider eurostat --dataset household_price_level_eu27 --due
```

A pasta de trabalho é privada e explícita. O worker não usa variáveis das bases
produtivas nem o token administrativo. Recusa sobreposição com caminhos configurados,
symlinks dos ficheiros de trabalho e inicialização de staging numa base preexistente
da aplicação. Um lock impede workers concorrentes na mesma pasta.

```sh
.venv/bin/python -m scripts.bulk_export \
  --staging /workspace/earnwage-bulk/staging.sqlite3 \
  --destination /workspace/earnwage-bulk/api-offline-new.sqlite3
.venv/bin/python -m scripts.bulk_inventory \
  --insights-db /workspace/earnwage-bulk/api-offline-new.sqlite3 \
  --acquisition-report /workspace/earnwage-bulk/acquisition.json \
  --output /workspace/earnwage-after
```

Exportação só para um ficheiro **novo**, excluindo quarentena. Uma última execução
falhada/incompleta de qualquer dataset impede exportação. Não configura Passenger,
não substitui bases existentes e não invoca imports/deployments administrativos.
A promoção a produção exige revisão, backup e integração autorizada no Data Manager
existente; este worker não expõe um novo endpoint administrativo.

## Limites, cache, revisões e agendamento

- Um a quatro datasets por invocação; transações de 250 observações.
- Downloads streaming limitados a 96 MiB; TSV expandido limitado a 256 MiB.
- Intervalo mínimo de um segundo entre pedidos, três tentativas, backoff exponencial
  e respeito por Retry-After. Pausas pedidas superiores a 60 segundos interrompem
  o job para reagendamento. 401/403/404 e falhas de proxy não provocam contorno de acesso.
- HTTPS verificado, apenas hosts registados; redirects desconhecidos são rejeitados.
- Cache SHA-256, freshness de uma hora, ETag/Last-Modified quando publicados.
  `--recheck` força revalidação. Os endpoints Eurostat consultados não forneceram
  esses validadores; fora do intervalo de freshness pode ser necessário descarregar
  novamente. Não se afirma uma ligação a um calendário oficial completo de releases.
- Retomada por página/ficheiro/checksum e checkpoint transacional. Um download de
  objeto interrompido recomeça; não há promessa de retomada por Range não verificada.
- Todas as versões ficam registadas. Revisões de uma observação aceite acima de
  30% são retidas para revisão. Para períodos novos, percentagens/índices 0–100
  usam limiar de 10 pontos absolutos; outras séries, 30% relativos. São heurísticas
  de revisão, não prova de que o valor oficial esteja errado. Flags Eurostat
  `b`, `d`, `u` exigem revisão; confidenciais não são importadas.
- Quarentena não bloqueia toda a evolução posterior: a comparação temporal usa
  observações publicadas adjacentes, enquanto revisões comparam o valor aceite.
  Não há comando de aprovação automática; a revisão/promoção continua manual.

`data/bulk_refresh_policy.json` define checks mensais dos datasets anuais,
trimestrais de salários/ILOSTAT e diários de câmbios. Estes últimos reutilizam o
provider existente; não foi implementado outro conector ECB. O HICP tem override
diário de verificação, sem descarga de ficheiros frescos. Não são ativados crons
no hosting nem alteradas as agendas produtivas existentes.

O novo workflow **Offline bulk data acquisition** executa apenas aquisição/staging
e retém cache e artefactos. Pode ser lançado manualmente; a agenda diária fica
**desativada por defeito** e depende de `EARNWAGE_BULK_CHECKS_ENABLED=true` no
repositório original. A política `--due` decide o que verificar em cada dia. O
workflow não escreve produção, não faz deploy e não usa o token administrativo.
Não foi executado remotamente nesta entrega. O estado offline é guardado mesmo
quando o import falha, para permitir retomada. Artefactos têm retenção de 14 dias.

## Fontes e acesso pendentes

O registo compara Eurostat, ILOSTAT, OECD, WDI, INE/GEP, BLS, Job Bank/StatCan,
RAIS/IBGE, ONS, BA e os institutos nacionais dos restantes países. Conserva
formatos, história, geografia, classificação, licenças/condições a confirmar e
frequências. Sem contagens estimadas fictícias; WDI/Eurostat têm agora contagens
medidas. As páginas/catálogos restantes não foram todos descarregados e validados
como datasets completos.

- OECD: o URL-base SDMX testado respondeu 403; confirmar dataflow e condições.
- MoSPI: respondeu 503 no teste; acesso/microdados oficiais continuam por verificar.
- INSEE, INE Espanha e FSO: os primeiros testes foram bloqueados pelo proxy do
  ambiente; os domínios necessários foram acrescentados ao rascunho, sem afirmar
  que a sua aplicação já tenha sido verificada.
- Job Bank (situação original da Fase 4, entretanto resolvida na 4B): redireciona o CSV para armazenamento público; o host de destino precisa
  de autorização no ambiente antes de uma aquisição completa. Os relatórios
  conservam o URL público do catálogo, não URLs temporários assinados.
- BLS (situação original da Fase 4, entretanto ampliada na 4B): o ZIP oficial respondeu 200 e anunciou 78 754 064 bytes; apenas
  uma pequena amostra foi lida. Não foi feita nova importação completa nem afirmado
  que as antigas restrições 403 se mantêm em todas as redes.
- RAIS/ECB: alguns URLs de descoberta sem seleção completa responderam 404;
  é necessário validar endpoint/release, não concluir inexistência da fonte.

Licenças e regras de divulgação devem ser confirmadas por dataset antes de
implementar os próximos conectores. Não houve contorno de autenticação/restrições.
A allowlist e instruções do worker foram guardadas no rascunho do ambiente; não
alteram segredos, rede ou configuração de produção.

## Validação automatizada da Fase 4 original

A suite de `main` contém 265 testes; os testes da PR fiscal #13 não foram copiados
para esta branch. Esta fase acrescenta testes de limites/retry/cache, atomicidade,
retomada, versões, quarentena, esquema/paginação, classificações, períodos,
fixtures reais com proveniência, exportação e leitura FastAPI/WSGI, proteção das
bases configuradas e isolamento do workflow. **Suite completa: 369 testes aprovados, zero falhados, em 69,39 segundos;
104 testes novos.** O dashboard foi também verificado em Chromium: 560 pares e
14 resultados ao filtrar nurse. Os resultados finais estão na evidência de aquisição. Mantém-se o aviso de descontinuação TestClient/httpx.

## Próximas tarefas pequenas e independentes

1. Confirmar a exportação do inventário produtivo e calcular novidades efetivas
   relativamente a produção, sem lhe escrever.
2. Validar releases históricos Job Bank anteriores a 2025, com versões NOC e
   esquemas próprios; a aquisição nacional/provincial/regional 2025 está concluída.
3. Validar os layouts e crosswalks SOC dos releases BLS anteriores a 2021;
   o histórico 2021–2025 e cobertura regional estão adquiridos na Fase 4B.
4. Adicionar catálogo/release metadata Eurostat para reduzir downloads sem ETag.
5. Ampliar INE/GEP e INSEE a anos disponíveis, depois de validar todos os códigos
   profissionais e definições; cada conector numa alteração própria.
6. Confirmar catálogo ILOSTAT e extrair apenas classificações suficientemente
   detalhadas; continuar a armazenar grandes grupos separadamente.
7. Implementar revisão explícita de quarentena com auditoria, sem trocar medidas,
   moedas ou populações; só depois integrar promoção autorizada no Data Manager.
8. Validar dataflows OECD e layouts oficiais RAIS/IBGE/MoSPI/PBS/CSO; não preencher
   profissões incompatíveis ou ausentes.

Phase 4C: ver a secção final de [PHASE4B.md](PHASE4B.md) e o
[procedimento de publicação](PUBLICATION.md). A revisão completa BLS e os pacotes
reutilizam os arquivos adquiridos, sem transferência para produção. A via Data
Manager fica desactivada por omissão e requer confirmação/checksum explícitos.
