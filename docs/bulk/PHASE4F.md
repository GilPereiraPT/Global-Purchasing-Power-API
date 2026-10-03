# Phase 4F — exportação salarial no Data Manager

Continuação da branch `docs/phase4e-first-publication`, PR #15. Esta funcionalidade
permite obter o inventário necessário à comparação Phase 4E através do **Data
Manager existente**, sem terminal nem nova interface de administração.
Não publica salários, não cria backups, não altera SQLite, não activa aquisição
ou publicação automática. Não se fez merge, deploy ou acesso à produção.

## Procedimento do operador

Depois de revisão/integração e instalação **separadamente autorizadas**, quando
esta funcionalidade estiver disponível na API e no Data Manager:

1. Obter autorização do proprietário para exportar o inventário. Essa autorização
   não vale aprovação de nenhum pacote salarial.
2. Abrir https://gilpereirapt.github.io/Global-Purchasing-Power-API/data-manager.html.
   Introduzir o token **existente** no campo próprio; não o alterar nem o copiar
   para URLs, consola, ficheiros ou relatórios.
3. Clicar em **«Exportar inventário salarial»** e confirmar a leitura/descarga.
   Manter a página aberta até concluir. Não é necessário activar a flag bulk,
   fazer backup, actualizar a API ou iniciar qualquer importação para exportar.
4. Guardar o ZIP num local privado. A mensagem «Inventário salarial gerado;
   descarga iniciada» confirma a resposta completa e o início da descarga pelo
   navegador; verificar a conclusão na lista de downloads do próprio navegador.
5. Enviar o ZIP, o SHA-256 apresentado no painel e a referência de autorização
   para normalização/comparação offline. Não colocar em Git/Pages/armazenamento público.
6. Limpar o campo do token e fechar a sessão quando terminar.

Se aparecer «Inventário NÃO exportado», não utilizar um ficheiro parcial nem
contornar limites. Os erros de autorização, rede, API sem a nova funcionalidade,
espaço/permissões, SQLite, metadata, schema e limites têm mensagens em português.
Confirmar a causa com o operador do hosting; não criar bases vazias ou modificar
dados para conseguir um export. Não repetir enquanto outra operação está em curso.

## Contrato e segurança

`POST /v1/admin/data-manager/salary-inventory`

```json
{"confirm":"export_read_only_salary_inventory"}
```

- Reutiliza `X-EarnWage-Admin-Token`, comparação constant-time, origem CORS
  autorizada, POST/OPTIONS, pedido JSON até 1 KiB e lock privado do Data Manager.
  Sem token válido, nenhuma leitura ou pasta temporária é iniciada. Não há GET
  de download, URL pública, token temporário ou novo segredo.
- Usa exclusivamente `GPP_CACHE_DB` já configurado: caminho absoluto, existente,
  privado, sem symlinks, coincidente com a base realmente activa. O cliente não
  fornece paths, SQL, tabelas ou URL. Não depende da base económica.
- A rota administrativa é tratada **antes** da inicialização pública WSGI: não
  chama loaders de snapshots, migrations/importers, conexão económica ou audit
  writes. SQLite abre com `mode=ro`, `query_only=ON` e uma única transacção de
  leitura, vendo dados WAL confirmados sem checkpoint ou `immutable=1`.
- Exporta apenas `us_oews`, `north_america_wages`, `ca_province_wages`, com colunas
  salariais enumeradas e chaves primárias reconhecidas. Tabelas ausentes são
  assinaladas; views, schemas/PK inesperados, valores não serializáveis/finitos
  ou metadata não segura fazem recusar todo o export. NULL não passa a zero.
- O manifest preserva schema `earnwage-salary-table-inventory-v1`, data UTC,
  âmbito das tabelas, contagens, versão SQLite, dimensões/modelo original e
  checksums SHA-256 de cada JSON. A referência de autorização HTTP é a indicação
  fixa da autenticação administrativa, nunca um valor/token enviado pelo utilizador.
- O ZIP inclui **só** `manifest.json` e os JSON de tabelas referenciados. Não inclui
  SQLite/WAL/SHM, senhas/token, configuração, paths privados ou outras tabelas.
  Nomes de source_file com paths, URLs com credenciais/query/fragment ou hosts
  não registados e metadata contendo o token/paths privados são recusados, sem
  reescrever os valores ou perder identidades silenciosamente.
- Confirma hashes enquanto empacota e gera SHA-256 do ZIP. A resposta usa
  `application/zip`, `Content-Disposition: attachment`, `Content-Length`,
  `X-EarnWage-Inventory-SHA256`, `nosniff`, `private, no-store` e CORS restrito.
  Nunca escreve credenciais, paths ou conteúdo salarial nos logs de erro.
- Só envia HTTP 200 depois de gerar o ZIP completo. O WSGI envia chunks de 64 KiB;
  o browser valida tipo, tamanho e presença de checksum antes de oferecer descarga.
  Uma falha na ligação não é apresentada como export completo nem gera descarga
  parcial. O operador pode comparar o hash do ZIP guardado com o painel.

## Limites e retenção exactos

Mantêm-se **100 MiB de JSON e 200 000 linhas no total**. Até quatro membros no ZIP;
limite do ZIP **101 MiB** incluindo overhead. Geração de JSON, hashes e compressão
partilham deadline cooperativa de **30 s**; espera SQLite até **5 s**. Leituras e
empacotamento são por linha/chunk, sem carregar bases/JSON completos na memória
do servidor. O browser mantém o Blob completo em memória até à descarga, pelo
que o operador deve ter capacidade para o limite de 101 MiB.

Antes de gerar, exige-se **265 MiB livres** no filesystem privado:
`2 × 100 MiB + 1 MiB de overhead ZIP + 64 MiB de reserva`. Confirmar também quotas
reais cPanel/conta; o filesystem preflight não garante quota ou espaço futuro.
JSON e ZIP podem coexistir temporariamente. Nenhuma permissão existente é
alterada para contornar uma recusa.

Temporários ficam só em
`<APP_ROOT>/_earnwage_backups/salary-inventory-exports/export-<id>`, fora de
`public_html`: pastas 0700, ficheiros 0600. Apenas subpastas com o prefixo/padrão
reservado são removidas; backups existentes e links/ficheiros de terceiros
permanecem intactos.

Política automática, **sem cron/schedule**:

1. Falha durante geração: remove a pasta nova incompleta antes de responder erro.
2. Descarga terminada ou iterable WSGI fechado por desconexão: tenta remover JSON,
   ZIP e pasta imediatamente. O iterable expira cooperativamente após **5 min**.
3. SIGKILL/crash ou falha de remoção podem deixar órfãos. Após **15 min** tornam-se
   elegíveis; são removidos automaticamente **no próximo pedido de exportação
   autenticado**, antes de gerar outro. Sem pedidos posteriores, não existe
   garantia de remoção exactamente aos 15 min; o operador deve inspeccionar a
   pasta privada após incidentes. Não se activou tarefa de limpeza/agendamento.
4. Até **quatro** exports temporários pendentes; novos pedidos são recusados até
   terminar/expirar/limpar os anteriores. O lock existente serializa geração,
   mantendo descarga separada para não bloquear backup durante a transferência.

A deadline é cooperativa e não interrompe syscalls/proxy bloqueados. O navegador
aborta o pedido após **90 s**; confirmar limites Passenger/proxy adequados no host.
O Blob URL local do navegador é revogado após 60 s/fecho da página; não é uma
ligação ao ficheiro no servidor. Ficheiros descarregados pertencem ao operador e
devem seguir a sua retenção privada, não são apagados pela API.

## Implementação e compatibilidade

O exportador Phase 4E foi extraído para `app/salary_inventory_export.py`, partilhado
pela CLI e pelo HTTP; não se mantêm duas implementações. `app/salary_inventory_download.py`
gere ZIP/stream/retention. O wrapper de documentação anterior delega na mesma CLI
num checkout completo; a alternativa no runtime é `python -m app.salary_inventory_export`.
Esta CLI guarda ficheiros permanentes autorizados, fora da retenção HTTP.

A allowlist de deployment existente já inclui ambos os módulos `app/*.py`.
**Não se alteraram scripts de deployment, workflows, token, Android, cálculo
salarial ou dados económicos.** O arquivo real de deployment foi criado e testado
numa instalação WSGI isolada; docs/helper/tests e exports/ZIP/SQLite não entram nele.
Os botões/handlers anteriores de actualizar API e backup são preservados. A mudança
WSGI é administrativa e aditiva; não altera contratos salariais públicos.

Testes exercitam autenticação/origem/métodos, confirmação exacta, WAL/read-only,
hashes, filtros de privacidade, schema/PK, limites/timeout/espaço, locks SQLite,
compressão/checksum falhados, limpeza/desconexão e órfãos, concorrência, JavaScript
real do botão com DOM/rede isolados e o Passenger extraído do arquivo real.
Os testes do browser são um harness Node, não um ensaio de rede/hosting real.

Continua necessário receber o inventário produtivo, normalizá-lo e comparar o
staging antes de seleccionar/autorizarem qualquer publicação. O candidato Phase
4E continua apenas candidato; esta funcionalidade não o publica nem transfere.
