# Phase 4E — primeira publicação salarial controlada

Preparação em 3 de outubro de 2026 (Europe/Lisbon). **Ainda não publicar.**
Não foi fornecido inventário produtivo autorizado nem autorização de um pacote.
Nenhum comando administrativo/SSH ou consulta à base produtiva foi executado
durante esta preparação. A instalação produtiva foi comunicada pelo operador;
o commit efectivamente instalado deve ser confirmado por ele antes da publicação.

## Estado verificado e falha suíça

O PR #14 foi integrado em `main` no commit
`105755b9d5f283641fd2d5dde521ac173aafcadd`. Os workflows API tests
[37123790444](https://github.com/GilPereiraPT/Global-Purchasing-Power-API/actions/runs/37123790444)
e [37123804460](https://github.com/GilPereiraPT/Global-Purchasing-Power-API/actions/runs/37123804460)
concluíram com sucesso nesse commit. Esta preparação parte desse main, não do PR #13.

O workflow [Swiss FSO #37123790395](https://github.com/GilPereiraPT/Global-Purchasing-Power-API/actions/runs/37123790395)
falhou, com exit code 1, no passo **Download national CH-ISCO-19 group wages from
FSO PXWeb**. A validação e retenção foram ignoradas; `propose-review` ficou
`skipped`. O trigger foi push ao main, para o qual esse job de publicação não é
autorizado. Não existe acesso SSH/HTTP ao EarnWage nesse workflow nem escrita
directa em main. Não prova refresh nem alteração de dados produtivos.

As APIs de job/check/annotations permitem confirmar esses factos. Os pedidos de
logs pelo CLI, API de job e arquivo do run devolveram corpos vazios neste ambiente;
o acesso HTTP directo à API de logs falhou com `ProxyError`. **A causa raiz permanece
por confirmar**: não atribuir a falha a 429, endpoint, layout ou disponibilidade
sem traceback. Os avisos Node 20/Ubuntu são annotations separadas, não diagnóstico.
O operador deve abrir o run, descarregar o log desse passo e fornecer a parte
FSO/traceback, sem segredos, para conclusão da análise. Não voltar a disparar o job.

Revisão estática: a requisição GET à tabela
`https://www.pxweb.bfs.admin.ch/api/v1/en/px-x-0304010000_205/px-x-0304010000_205.px`
é anterior ao POST estatístico. Só HTTP 429 é repetido; outros erros HTTP/rede,
variáveis inexistentes ou layout inesperado abortam. Existe fallback de `total()`
para a primeira categoria quando não encontra um total: qualquer correcção futura
deve substituir essa suposição por validação explícita do âmbito, em trabalho
separado com metadata oficial. Não se corrigiu ou executou este importador aqui.
A fonte suíça publica grupos profissionais; não entra no primeiro pacote US/CA.

## A. O que o operador fornece agora: só inventário autorizado

1. Registar autorização do proprietário **para exportar o inventário**, com data
   e referência de aprovação. Isto não autoriza backup, importação ou publicação.
2. Confirmar no cPanel o caminho **já utilizado pela aplicação** em `GPP_CACHE_DB`.
   Não procurar bases automaticamente, criar bases vazias, trocar caminhos ou
   imprimir `.env`/token. O Python do terminal deve ser o da aplicação instalada.
3. Criar uma pasta privada de trabalho, fora de `public_html`, com permissões 0700.
   Copiar apenas o helper de documentação abaixo para essa pasta. Não actualizar
   o runtime para o executar: é autónomo, usa a biblioteca standard e não importa app.
4. Executar uma única exportação com o caminho explícito e uma pasta de saída nova.
   A conta do operador deve já ter autorização e leitura da base e do WAL/SHM.
   Não alterar permissões da base, executar checkpoint, VACUUM ou usar `immutable=1`;
   esse último poderia omitir dados recentes em WAL.

Helper: [operator/export_salary_inventory.py](operator/export_salary_inventory.py).
SHA-256 do helper revisto:
`71d943701c0d704bc59079ec1d132ebea5b0a11f2fd43d386a9b6bf3a0d44e17`.

Exemplo a adaptar pelo operador, nunca executado por esta revisão:

```bash
umask 077
mkdir -m 700 /ABSOLUTO/PRIVADO/phase4e-operador
sha256sum /ABSOLUTO/PRIVADO/phase4e-operador/export_salary_inventory.py
/PYTHON/DA/APLICACAO/python /ABSOLUTO/PRIVADO/phase4e-operador/export_salary_inventory.py \
  --wages-db /CAMINHO/REAL/JA/CONFIGURADO/wages.sqlite3 \
  --output /ABSOLUTO/PRIVADO/phase4e-operador/inventario-novo \
  --authorization 'referencia-da-aprovacao-apenas-do-inventario'
```

O helper abre a base com `mode=ro`, `query_only=ON` e uma transacção de leitura
consistente para as três tabelas: `us_oews`, `north_america_wages` e
`ca_province_wages`. Exporta todas as linhas dessas tabelas, só as colunas salariais
enumeradas, incluindo identidades, unidades, períodos originais, fontes e NULL.
Não exporta tabelas económicas, caches, utilizadores ou credenciais. Tabelas
ausentes são assinaladas; schemas inesperados recusam a operação, sem inicializar
ou corrigir a base. A leitura pode ter locks de curta duração; em WAL utiliza a
coordenação SQLite existente, sem checkpoint/escritas lógicas na base ou WAL.
Se o modo/SHM/permissões do hosting impedirem leitura, parar, não forçar mudanças.

Limites: **100 MiB, 200 000 linhas no total, deadline cooperativa de 30 s**, espera
SQLite até 5 s; memória por linha/chunk, não por base. Exige 164 MiB livres na pasta
de saída (limite + reserva). Ficheiros 0600/directório 0700. Uma falha remove só o
directório novo incompleto; nunca se entrega inventário parcial como completo.
SIGKILL pode deixar pasta sem manifest: não é um export válido. Se ultrapassar
limites, rever uma exportação explicitamente circunscrita, sem contornar limites.

Entregar **manifest.json e todos os JSON de tabelas referenciados no manifest**,
com a referência de autorização. Podem ser enviados juntos num ZIP privado;
não enviar SQLite/WAL/SHM, backups, configuração, token nem arquivos BLS/Job Bank.
O manifest contém hashes individuais, presença/contagens/schema das tabelas,
versão SQLite, data UTC e tamanhos de base/WAL, sem caminhos privados.
Os hashes verificam integridade; não substituem a confirmação da origem pelo operador.

**Não serve:** o JSON/CSV do dashboard `/v1/data-inventory`, por ser agregado.
Esta exportação bruta tem schema `earnwage-salary-table-inventory-v1`; ainda não
é o protocolo `earnwage-observation-inventory-v1` descrito em
[INVENTORY_EXPORT.md](INVENTORY_EXPORT.md). Não passá-la directamente ao comparador.

## B. Comparação e escolha offline, após receber o export

Não voltar a adquirir os arquivos. Reutilizar os staging aceites Phase 4B:

- BLS: `/workspace/phase4b-bls-final/staging.sqlite3`, releases SOC2018 2021–2025.
- Job Bank: `/workspace/phase4b-canada/staging.sqlite3`, release NOC2021 2025;
  `2023-2024` permanece um período plurianual, não dois anos artificiais.

Estas localizações são artefactos desta estação, não caminhos de produção.
A comparação fica **indisponível**, e não zero, enquanto faltar o export.
Após autorização da sua utilização:

1. Verificar manifest, hashes, schema, data, limites e completude das tabelas.
2. Normalizar offline os registos reconstruíveis no protocolo existente:
   fonte/dataset, país, geografia, período, medida, unidade/moeda, classificação
   e dimensões. Para BLS preservar indústria/ownership/o_group e distinguir
   SOC2018 de anos anteriores; para CA preservar NOC2021 e geografia exacta.
   Rever a fonte literal, versões, aliases e colisões antes de deduplicar.
   NULL continua NULL. Identidades divergentes/ambíguas não são ausências demonstradas.
3. Comparar também as observações BLS da tabela `north_america_wages`, não apenas
   `us_oews`; a mesma observação oficial pode existir noutro modelo. Dados de outras
   fontes não passam a ser duplicados BLS por terem valor semelhante.
4. Registar uma lista explícita de âmbitos cuja presença/ausência é demonstrável.
   Se nem todas as identidades são reconstruíveis, usar `scope: partial` e bloquear
   afirmações globais de novidade. Ausência de identidade num export parcial não
   prova ausência em produção. Não descartar ambiguidades silenciosamente.
5. Usar o comparador/dashboard **existentes**, com ficheiro normalizado autorizado,
   sem ligação à produção. A referência de autorização é metadado, não um token.

```bash
.venv/bin/python -m scripts.bulk_compare_inventory \
  --staging /workspace/phase4b-bls-final/staging.sqlite3 \
  --inventory /PRIVADO/inventario-normalizado.json --authorization referencia
.venv/bin/python -m scripts.bulk_compare_inventory \
  --staging /workspace/phase4b-canada/staging.sqlite3 \
  --inventory /PRIVADO/inventario-normalizado.json --authorization referencia
.venv/bin/python -m scripts.bulk_inventory \
  --staging /workspace/phase4b-bls-final/staging.sqlite3 \
  --staging /workspace/phase4b-canada/staging.sqlite3 \
  --production-inventory /PRIVADO/inventario-normalizado.json \
  --inventory-authorization referencia --output /PRIVADO/relatorio-phase4e
```

O dashboard é gerado fora do Git e do pacote produtivo. Separar observações
realmente novas, revisões, duplicados, em falta e âmbitos não comparáveis. As
revisões não entram na primeira publicação. Separar células estatísticas de linhas
SQL e de pares país/profissão: aliases não criam observações adicionais.

Escolha: uma só linha nacional histórica, ano mais antigo validado e profissão
com correspondência exacta; conservar juntas todas as suas medidas aceites.
Se alguma medida já existir na mesma linha-alvo, esta via não a completa nem
substitui: preview protege a linha inteira, mesmo com NULL. Escolher outro alvo
ou declarar que não há pacote útil. Não publicar pacotes compostos só de duplicados.
Regiões/quarentena/revisões e grupos amplos ficam fora deste primeiro ensaio.

## C. Candidato preparado, ainda não seleccionado

[Evidência compacta](phase4e-candidate.json), sem dataset completo no Git:

| Campo | Candidato para avaliação |
| --- | --- |
| Fonte/âmbito | BLS OEWS, US nacional, SOC2018 `15-1252`, software_developer |
| Período original | May 2021 |
| Medidas | Média, mediana, P10/P25/P75/P90, nas duas unidades originais |
| Dimensão | Cross-industry `000000`, ownership `1235`, detailed |
| Tamanho | **12 células, 1 linha SQL, 9 182 bytes** |
| Pacote SHA-256 | `dbf36d12a63427e77a4d60d076bd55ef844faa5bd47bd5bc3d4ec67e886f60c9` |
| Arquivo oficial SHA-256 | `4dc5c9db9e111a06e612e848e107488a7beec0743853f02b1a3a069bb48207ce` |
| Aquisição original | 2026-10-03T03:26:41.492053+00:00 |

O pacote privado encontra-se nesta estação em `/workspace/phase4e-preparation/`,
não foi transferido. URL original: https://www.bls.gov/oes/special-requests/oesm21all.zip.
O builder existente voltou a verificar o staging accepted, run final completo,
artefacto registado e projecção; não fez download. Preview numa base temporária
carregada **só com o snapshot Git** deu 1 linha nova/0 duplicadas/0 protegidas.
Isto **não é novidade comprovada em produção**, nem autorização. O export pode
invalidar este candidato; nesse caso seleccionar outro e calcular novo checksum.
Não se promete novo par país/profissão: trata-se de potencial histórico adicional.
CA só entra se o inventário demonstrar um alvo nacional realmente ausente.

## D. Checklist a preencher antes de qualquer publicação

- [ ] Inventário autorizado recebido, hashes revistos e normalização validada;
      âmbito do alvo comprovadamente completo. Data/SHA do inventário registados.
- [ ] Pacote exacto seleccionado, só aceites realmente novas, sem revisões, NULL,
      flags/quarentena; classificação/versão/dimensões/fonte originais verificadas.
- [ ] Registar SHA-256 do pacote, bytes, profissão/ano, células e linhas esperadas;
      até 1 000 células/2 MiB. Não alterar o ficheiro após aprovação.
- [ ] Proprietário autoriza **essa publicação**, por escrito, pelo checksum exacto,
      âmbito, contagens, validade/janela e operador. Exportação não vale autorização.
- [ ] Operador confirma `/v1/health`: status ok e commit instalado exacto aprovado;
      confirmar main/CI sem actualizar deployment, código, token ou Android.
- [ ] Python 3.11/3.12 e `sqlite3.sqlite_version` do Python **real do Passenger**;
      SQLite >=3.24 pelas operações UPSERT do runtime existente. Registar versão
      exacta e validar cópia/recuperação com a mesma build num ambiente isolado.
      JSON1 é requisito das ferramentas offline, não da publicação no hosting.
- [ ] `GPP_CACHE_DB` e `EARNWAGE_INSIGHTS_DB`: caminhos persistentes absolutos,
      existentes, distintos e coincidentes com as bases activas. Cada base+WAL
      <=256 MiB. Não criar base vazia para satisfazer preflight.
- [ ] Filesystem Linux local com flock/locking SQLite fiável; utilizador Passenger
      com leitura/escrita nas bases e criação de journal/WAL/SHM. Pastas de pacotes,
      backups e recuperação privadas 0700, ficheiros 0600, sem symlinks/public_html.
      Token/origem HTTPS existentes; nunca copiar o token para comandos ou relatórios.
- [ ] Medir D=sum(base+WAL das duas bases), S=sum(JSON de data), quota e espaço
      livre efectivo no filesystem de backup. Antes **de cada** backup exige-se
      **3×D + S + 64 MiB** livres. `df` não substitui a quota cPanel. Reservar ainda
      D+S para restore e retenção das cópias já feitas; pode haver backup manual,
      backup da publicação e backup do rollback. Sem pruning automático.
- [ ] Deadline de backup 30 s cooperativa, lock da publicação até 5 s, pedido/worker
      >=60 s após validar I/O real; sem writers/importadores concorrentes nesta janela.
      Não alterar/agendar importadores para esta operação.
- [ ] Backup manual do Data Manager bem-sucedido, duas bases com integrity ok;
      ID/manifest/hashes e cópia externa privada registados. Testar restore para
      **pasta nova isolada**, sem ligar workers ou trocar configurações activas.
      Definir retenção e responsável pela recuperação.
- [ ] SHA do pacote verificado novamente após transferência privada; preview
      deve coincidir com a aprovação: linhas novas >0, duplicadas/protegidas =0.
      Se diferir, parar e rever autorização; não adaptar o pacote em produção.
- [ ] Flag bulk ausente/false até cumprir os gates. Activação temporária manual
      apenas após aprovação; nada altera `EARNWAGE_DEPLOY_ENABLED`, cron ou segredos.

Modelo de autorização: «Autorizo o operador [nome] a publicar o pacote SHA-256
[hash], [bytes], [fonte/país/geografia/classificação/período], [células]/[linhas]
novas, baseado no inventário [hash/data], na janela [data/hora Europe/Lisbon],
condicionado ao preview sem duplicados/conflitos e aos backups/recuperação validados.»
Não preencher nem presumir esta aprovação pelo proprietário.

## E. Execução futura pelo operador, no Data Manager existente

**Só depois da checklist e autorização do pacote. Estes passos não foram executados.**

1. Abrir https://gilpereirapt.github.io/Global-Purchasing-Power-API/data-manager.html,
   inserir o token existente no campo próprio e usar «Verificar acesso/configuração»
   e «Criar e verificar cópia de segurança». Não clicar em actualizar API/importações.
   Exigir backup `available` e integrity ok em ambas as bases. Ensaiar a recuperação
   dessa cópia para pasta nova antes de continuar.
2. Pelo Gestor de Ficheiros privado cPanel, colocar **só o pacote aprovado** em
   `<APP_ROOT>/_earnwage_backups/bulk-packages/<checksum>.json`, 0700/0600. Não
   copiar índices grandes, staging, ZIP/XLSX/CSV de aquisição ou bases.
   `sha256sum` do ficheiro deve ser igual ao nome e à autorização.
3. Só o operador activa temporariamente `EARNWAGE_BULK_PUBLICATION_ENABLED=true`
   na aplicação. Se exigir reinício Passenger, verificar novamente health/commit;
   nenhum deployment ou alteração de caminhos/token faz parte da operação.
4. O UI actual tem backup/status mas ainda **não tem botões bulk**. Usar a função
   `admin()` já existente nessa página, na consola do navegador, na origem GitHub
   autorizada. Rever o código; não colar tokens na consola. Executar uma chamada
   de cada vez e guardar apenas resultados, nunca headers ou sessões de rede.

Preview (substituir pelo checksum realmente autorizado, não assumir o candidato):

```javascript
await admin("bulk-preview", {checksum: "CHECKSUM_APROVADO_64_HEX"})
```

Exigir `status: review_required`, inserted_rows igual ao aprovado, duplicate_rows
e protected_existing_rows iguais a zero. `publication_disabled` não é preview
validado. A comparação é repetida sob lock/transacção na publicação, mas o inventário
e a janela sem writers continuam necessários para sustentar a novidade estatística.

Publicação — **chamada separada, só com aprovação válida e preview coincidente**:

```javascript
await admin("bulk-publish", {
  checksum: "CHECKSUM_APROVADO_64_HEX",
  confirm: "publish_reviewed_salary_package"
})
```

Guardar checksum, status `published`, inserted_rows, duplicate_rows,
protected_existing_rows, backup_id e hora. O Data Manager faz outro backup fresco
das duas bases antes da escrita. `already_published` é idempotência, não uma nova
aquisição. Não repetir pedidos automaticamente nem publicar os restantes pacotes.

5. Confirmar o histórico e o período original na API. Para o candidato, se aprovado:
   `/v1/us/oews/wages/15-1252?year=2021&area=99`; comparar as 12 medidas originais,
   unidade, fonte e observação `May 2021`. Verificar que respostas existentes e os
   salários mais recentes não mudaram. Publicar histórico não muda automaticamente
   a overview de salários mais recentes nem calcula poder de compra líquido.
6. Se houver falha/timeout após enviar a chamada, **não assumir ausência de commit**.
   Guardar resultado/backup_id quando disponível, fazer preview e rever o journal
   no processo operacional. Uma repetição manual do checksum aprovado pode devolver
   `already_published`; não editar o ficheiro ou enviar outro checksum para contornar.
7. Se for necessário rollback, obter autorização operacional e executar a chamada
   separada abaixo. Cria backup novo e remove só linhas próprias não modificadas:

```javascript
await admin("bulk-rollback", {
  checksum: "CHECKSUM_APROVADO_64_HEX",
  confirm: "rollback_reviewed_salary_package"
})
```

Exigir `rolled_back` e removed_rows esperadas. Edição posterior/linha ausente faz
recusar integralmente: parar e recuperar manualmente. Não correr VACUUM durante
a janela de rollback: o journal usa rowid e a reorganização pode invalidá-lo.
8. Para recuperação completa, reutilizar o script instalado, com destino novo:

```bash
cd /APP_ROOT_EXISTENTE
/PYTHON/DA/APLICACAO/python -m scripts.restore_earnwage_data \
  --backup /ABSOLUTO/PRIVADO/backup-ID \
  --output /ABSOLUTO/PRIVADO/nova-recuperacao
```

Valida hashes/integridade e cria cópias; não troca as bases activas. Qualquer troca
posterior exige manutenção, aplicação parada, autorização e preservação da
configuração. As duas bases não têm snapshot atómico conjunto; controlar writers.
9. Ao concluir ou abortar, desactivar a flag bulk (false/ausente), verificar o
estado após eventual reinício e limpar o campo de token/fechar a sessão do browser.
Conservar relatório, pacote/índice, autorização, backups e hashes em armazenamento
privado segundo retenção; não publicar logs ou inventário em GitHub Pages.

## Bloqueios actuais

Validação desta preparação: **498 testes aprovados, 0 falhados**, incluindo
11 casos novos do exportador (WAL, valores/NULL, fonte intacta, exclusão de dados
privados, permissões, ausência de tabelas e falhas/limites). Mantém-se um aviso
herdado TestClient/httpx. Os 35 workflows passam no actionlint 1.7.12, sem
ShellCheck/Pyflakes. Todos os novos ficheiros docs/testes são recusados pela
allowlist produtiva existente; não se altera nenhum módulo app/scripts ou workflow.

- Inventário produtivo e autorização da sua utilização ainda não fornecidos.
- Novidade do candidato, pacote seleccionado e autorização de publicação pendentes.
- Espaço/quotas, SQLite/locking/permissões, versão instalada e recuperação no hosting
  por confirmar pelo operador; não se extrapolam os ensaios locais para produção.
- Causa raiz suíça pendente de log acessível; tratamento separado, fora do pacote.

Nada activa publicação automática, altera deployment/token/Android, ou integra
o PR #13. A primeira publicação só poderá avançar depois de remover os bloqueios
do alvo escolhido; cobertura regional/quarentena continua fora do seu âmbito.
