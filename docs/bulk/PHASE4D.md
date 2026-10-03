# Phase 4D — validação antes de merge

Data: 2026-10-03. PR #14, branch `feat/bulk-data-coverage`. Não se acedeu à
produção, não houve merge/deploy e não se activou aquisição ou publicação agendada.

**Decisão:** a implementação restrita passou nos ensaios locais e pode seguir para
revisão humana. **A publicação produtiva continua bloqueada**, desactivada por
omissão, até cumprir a checklist abaixo. Não se declara capacidade ou configuração
do hosting sem as verificar; nenhuma base usada nesta fase veio de produção.

## Auditoria do PR completo

Revistos módulos de aquisição/ledger, parsers, mapeamentos, inventário/exportação,
Data Manager, alterações WSGI, workflows, documentação e testes, contra `main`.
As alterações de parser BLS são condicionadas por `bulk=True`; o modo anterior
mantém comportamento. O leitor bulk CA é adicional; o leitor provincial anterior
não muda. Não se alteram cálculos salariais/fiscais ou contratos públicos.
Os novos endpoints são administrativos WSGI do Data Manager, não uma API paralela.
O staging permanece separado das bases da aplicação, com importações/exclusões
explícitas e sem acesso produtivo por caminhos descobertos automaticamente.

Problemas encontrados e corrigidos nesta fase:

| Problema | Correcção / verificação |
| --- | --- |
| Backup sem verificação de espaço | Recusa antes de criar destino se o orçamento livre não chega |
| Backup podia esperar indefinidamente por SQLite | Deadline cooperativo de 30 segundos, cópia por 256 páginas e callback; teste com lock exclusivo em DELETE |
| Backup falhado podia deixar pasta parcial | Limpeza apenas do destino novo em excepções, incluindo `KeyboardInterrupt`; nenhuma pasta preexistente removida |
| Três workflows herdavam permissões globais do repositório | `contents: read` explícito em `tests.yml`, `audit-canada-noc.yml` e `inspect-north-america.yml` |

### GitHub Actions

Os **35 workflows** têm permissões de topo `contents: read`. Apenas os dez jobs
`propose-review` pedem escrita de conteúdo/PRs, e exigem simultaneamente dispatch
manual, repositório original e ref `main`. O helper valida novamente esses critérios,
SHA de base e ficheiros autorizados; só cria refs `data-review/…`, nunca actualiza
`main`. Não existe `git push` nos workflows. Jobs automáticos de leitura, Pages e
limpeza de Actions conservam as permissões específicas de que necessitam, sem
escrita de conteúdo em `main`. Não se activou qualquer variável ou cron.

Testes negativos cobrem push, schedule, PR, fork, refs diferentes e SHA inválido.
A [auditoria por workflow](workflow-publication-audit.json) foi actualizada.
`actionlint 1.7.12`, sem ShellCheck/Pyflakes, aprova agora os **35 workflows,
sem alertas**. Na revisão final corrigiu-se apenas `if: >` para `if: >-` em
`deploy-production.yml`: elimina a quebra de linha literal fora de `${{ }}`,
que o linter interpretava como uma condição sempre verdadeira. Comparação YAML
antes/depois confirmou que o predicado é exactamente igual, excepto esse sufixo.
A correcção torna explícita a condição booleana pretendida; não alarga a autorização.
Mantêm-se todos os critérios: activação explícita, repositório original, push,
testes concluídos com sucesso, main e origem original. Não se alterou a variável
de activação, os passos SSH, segredos ou o deployment pelo Data Manager.
Acrescentou-se regressão para impedir o reaparecimento de texto fora da expressão.
Os runs SSH desta branch devem continuar `skipped`; não se executou deployment.
Não se verificaram regras de branch protection, permissões administrativas ou
segredos do repositório. A análise garante o comportamento dos workflows versionados;
protecção de `main` contra outros actores exige regras externas do GitHub.

## Sequência operacional e falhas

O teste do arquivo real instala-o **num directório temporário**, importa
`passenger_wsgi.application` num processo novo e usa bases locais com snapshots
Git, schemas reais e um indicador económico de controlo. Impede pedidos de rede.
Confirma ausência de imports FastAPI/a2wsgi e executa:

1. Criação do pacote a partir de staging isolado, com checksum e índice.
2. Preview pelo endpoint autenticado, antes de qualquer escrita salarial.
3. Publicação com confirmação e backup fresco.
4. Repetição do checksum, sem duplicados.
5. Reinicialização do WSGI/snapshots, mantendo a linha histórica publicada.
6. Rollback, removendo só a linha inserida e preservando a baseline.
7. Recuperação do backup para novas cópias, verificando salários e indicador.
8. Comparação exacta das respostas anteriores/posteriores: health, países,
   profissões, salários US/CA e salário provincial canadense.

Este cenário automatizado é **sintético para testar o protocolo**, não uma nova
aquisição nem validação estatística. Separadamente, reutilizaram-se os cinco
pacotes reais Phase 4C, provenientes dos arquivos oficiais já adquiridos, em bases
novas locais carregadas exclusivamente dos snapshots Git. Resultado reproduzido:
**112 linhas históricas inseridas, 2 596 linhas duplicadas, zero conflitos**, cinco
repetições idempotentes, rollback completo e recuperação com integridade `ok`.
Ver [evidência operacional](phase4d-operational-evidence.json).

| Falha testada | Resultado esperado confirmado |
| --- | --- |
| Espaço insuficiente antes do backup | HTTP 503; sem publicação ou backup elegível |
| ENOSPC injectado durante cópia de snapshot | Sem publicação; pasta incompleta removida; fontes preservadas |
| Base salarial ou económica ausente | HTTP 409; ficheiro não recriado |
| Segunda operação com lock Data Manager | HTTP 409 `another_import_is_running` |
| SQLite DELETE com lock exclusivo no backup | Timeout cooperativo; destino incompleto removido |
| SQLite WAL com writer lock na publicação | `BEGIN IMMEDIATE` falha após cerca de 5 s; sem importação parcial |
| SQLite realmente `FULL`, via `max_page_count` | Transacção abortada; dados anteriores preservados |
| `KeyboardInterrupt` no backup | Destino novo removido; backups anteriores intactos |
| Processo morto com `SIGKILL` durante INSERT | SQLite recupera a transacção; zero linhas publicadas, integridade `ok` |
| Resposta perdida depois de commit | Repetição devolve `already_published`, sem duplicação |
| Edição posterior de linha publicada | Rollback integral recusado; recuperação manual exigida |
| Checksum/schema/PK incompatível | Recusa sem sobrescrever dados |

Os testes ENOSPC não esgotam o disco físico da máquina: injectam o erro de I/O;
`SQLITE_FULL` usa o limite real de páginas SQLite. Um `SIGKILL` durante backup pode
impedir a limpeza Python e deixar uma pasta parcial sem manifest. Esta não é backup
elegível; inspeccionar e limpar manualmente depois, preservando os backups válidos.
A deadline é cooperativa: não interrompe uma syscall bloqueada nem substitui os
timeouts do Passenger/proxy. Os snapshots/backups das duas bases são consistentes
individualmente, mas não constituem snapshot atómico entre bases.

## Compatibilidade e requisitos exactos

- Linux com `fcntl.flock`, SQLite e filesystem local com locking fiável. NFS/locks
  inconsistentes não foram validados.
- Python **3.11 ou 3.12**: 3.12 testado localmente; CI usa 3.11. Instalar e verificar
  as dependências de `requirements.txt`, incluindo `httpx` e `openpyxl`. A entrada
  produtiva continua a ser WSGI nativo; não é necessário arrancar uvicorn/FastAPI.
- Para ferramentas offline, SQLite com JSON1 (`json_extract`). Não instalar o
  ledger, ZIP ou CSV completos no hosting. A publicação usa as tabelas salariais
  existentes e valida nomes de colunas e chaves primárias.
- `GPP_CACHE_DB` e `EARNWAGE_INSIGHTS_DB` absolutos, distintos, existentes, privados
  e graváveis; preservar os caminhos e configuração. Limite por base incluindo
  WAL: **256 MiB** nesta via. Não contornar esse limite para incluir bases maiores.
- `_earnwage_backups` e `bulk-packages` privados, fora de `public_html`: directórios
  0700, pacotes/backups 0600. Permissões de leitura, escrita e criação de ficheiros
  temporários para o utilizador do Passenger, e espaço suficiente no filesystem
  de destino. Snapshot do ambiente/token não integra os pacotes.
- Token administrativo existente, HTTPS e origem CORS já autorizada. Não guardar
  token em relatórios ou argumentos. Só o checksum de 64 hex e confirmação cabem
  no pedido administrativo, limitado a 1 KiB.
- Pacote: até **1 000 células / 2 MiB**. Publicação SQLite: espera por lock até **5 s**.
  Backup: deadline cooperativa **30 s**. Recomenda-se timeout do pedido/worker de
  pelo menos **60 s**, mas validar latência/I/O no hosting antes de activar.
- Manutenção sem writers concorrentes para uma recuperação completa. Não trocar
  caminhos de bases com workers activos. Rollback journal não depende dessa troca.
- `EARNWAGE_BULK_PUBLICATION_ENABLED` ausente/false durante revisão. A activação
  futura é manual e separada de aquisição e SSH. Nenhum novo segredo foi criado.

O arquivo produzido pelo mecanismo actual inclui módulos `bulk_*`, as dependências
internas de mapeamento, registos JSON necessários e scripts de criação de pacotes,
backup/restauração. Não inclui docs/dashboards, bases, `.env`, ZIP/XLSX ou cache de
aquisição. O teste verifica esses membros e executa o WSGI extraído. A capacidade
de importar no servidor real não foi verificada por falta de acesso autorizado;
é um pré-requisito operacional, não uma conclusão deste ensaio.

## Armazenamento, memória e riscos

Definir **D** como a soma dos bytes das duas bases e WAL e **S** como os snapshots
JSON do runtime. Antes de backup exige-se espaço livre conservador:

`3 × D + S + 64 MiB`

O backup consome aproximadamente `D + S`, além do manifest, podendo crescer se
outras ligações escrevem durante a cópia. São guardados backups novos nas tentativas
de publicação **incluindo repetição**, e antes de rollback. Não existe pruning
automático: a retenção/cópia externa deve ser definida pelo operador. Cinco
publicações, cinco repetições e cinco rollbacks podem gerar **15 backups**.

Nesta baseline: bases após o ensaio **2 265 088 + 28 672 bytes**, pacotes
**3 464 907 bytes**, snapshots de runtime **4 883 495 bytes**. O ensaio sem copiar
os snapshots de runtime gastou **37 324 736 bytes** em backups; com os snapshots
completos, estimar adicionalmente cerca de **15 × 4,88 MB**, sujeito a WAL/SQLite.
Não são medições da produção. No máximo permitido (duas bases de 256 MiB), o
orçamento prévio aproxima-se de **1,57 GiB livres**, acrescido da retenção já
ocupada e do espaço de recuperação. Reservar uma cópia extra `D + S` para restore.

Reutilização dos cinco pacotes: **1,548 s** e pico do processo **43 360 KiB** neste
ambiente, com uma baseline pequena e snapshots de backup vazios. Não extrapolar
para 256 MiB ou para limites cPanel. O teste WSGI completo passa com snapshots reais,
mas limites de memória/I/O e arranque frio no host continuam por medir. Na estação
de aquisição, o workspace BLS existente ocupa cerca de **2,7 GiB** e o canadense
**67 MiB**; esses arquivos ficam fora do runtime e do Git.

Riscos residuais: crescimento dos backups/journal; fim de espaço após preflight;
commit salarial confirmado seguido de falha no log económico (repetir checksum,
não assumir ausência de commit); locks/worker timeouts; indisponibilidade temporária
em recuperação; snapshots iniciais usam o comportamento herdado de carga e devem
ser revistos quando houver valores produtivos divergentes. Preservar pacotes/índices
para auditabilidade: checksum não certifica por si só a autenticidade da fonte.
Não há rollback simultâneo das duas bases; restore completo exige controlo operacional.

## Checklist final e bloqueios

Para revisão/integração:

- [x] PR completo revisto; alterações de API/parser antigas preservadas nos testes.
- [x] Nenhum workflow sem permissões explícitas; escritores manuais separados.
- [x] Sequência completa WSGI/arquivo de deployment validada localmente.
- [x] Falhas/interrupções/locks testados; espaço e deadline de backup corrigidos.
- [x] Suite completa: **487 aprovados, 0 falhados**, um aviso herdado TestClient/httpx.
- [x] Alerta herdado `if-cond` resolvido por chomping YAML, sem alterar os
      critérios de autorização nem activar SSH; 35 workflows sem alertas.
- [ ] Revisão humana do PR e checks do commit final; **não fazer merge nesta tarefa**.

Para autorizar uma futura publicação produtiva:

- [ ] Exportação produtiva **explicitamente autorizada**, comparação read-only e
      revisão do pacote exacto; a baseline Git não comprova diferenças em produção.
- [ ] Operador confirma versões Python/SQLite, dependências, paths, schemas/PK,
      permissões, orçamento livre, quotas cPanel, latência e timeouts.
- [ ] Definir retenção, cópia externa, manutenção e ensaio de recuperação no host
      isolado apropriado, sem tocar na produção durante esta revisão.
- [ ] Verificar protecção externa de `main`, criação de PRs pelo GITHUB_TOKEN e
      checks sobre propostas de dados. Configuração GitHub não foi alterada.
- [ ] Preservar token/configuração; activar manualmente a via de publicação só
      depois dessas verificações. Aquisição/schedules/SSH continuam separados.

Bloqueios de cobertura, sem aprovação automática: **13 565 quarentenas BLS**;
**13 mapeamentos em falta**; definições NOC originais inacessíveis nesta sessão;
metadados regionais BLS incompletos para esta projecção; ausência de tabela/API
existente para regiões económicas CA; medidas nacionais CA fora do contrato
média/mediana. Impedem expansão desses âmbitos, não entram nos pacotes restritos.
Não se apresentam observações sintéticas ou grupos amplos como novos salários.

O PR #13 mantém-se independente. Android, cálculos económicos/fiscais, segredos,
base produtiva e activações de schedules/deployment não foram alterados.

## Revisão final de integração

A publicação bulk continua desactivada com variável ausente, vazia, `false`,
`TRUE` ou `1`; só o valor exacto `true` permite prosseguir. Os três endpoints
(preview/publicação/rollback) exigem o token administrativo existente mesmo quando
activados. Dezoito novos casos cobrem esses controlos; a autorização é anterior
ao processamento da operação. Publicar e reverter exigem ainda confirmação
explícita, checksum, bases compatíveis e backup fresco. Não há publicação agendada.

O empacotador usa apenas ficheiros Git autorizados: Python em app/scripts,
requirements, entrada WSGI e JSON imediatamente sob data. Os snapshots JSON
versionados existentes são necessários para preservar a API; não são os arquivos
de aquisição. Dashboards gerados, staging SQLite, pacotes de publicação, caches,
CSV/ZIP/XLSX e arquivos completos de aquisição ficam fora do deployment. O arquivo
real e o WSGI extraído foram testados em isolamento, incluindo backup/restauração.
O workflow de deployment existente do Data Manager conserva o seu filtro de
ficheiros e a verificação do commit main com testes aprovados.

Os bloqueios produtivos da checklist mantêm-se: exportação autorizada para
comparação, validação do hosting, retenção/recuperação e configuração externa de
protecção/PRs do GitHub. O alerta actionlint deixou de ser bloqueio. A revisão
local não autoriza merge, activação, publicação ou deployment.
