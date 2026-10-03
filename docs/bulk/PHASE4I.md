# Phase 4I — recuperação e publicação controlada pelo Data Manager

Esta fase acrescenta controlos ao painel existente. Não muda o token, deployment,
Android, cálculos ou valores salariais preexistentes. Não executa operações em
produção durante a implementação. As instruções da Phase 4H que referiam ausência
de botões de publicação/recuperação descrevem a versão anterior; aplicar este guia
apenas quando a versão Phase 4I tiver sido instalada por processo separado.

## Sequência antes de publicar

1. Abrir o Data Manager existente por HTTPS. Introduzir o token administrativo
   existente no campo próprio; nunca o guardar em ficheiros/consola/relatórios.
   Confirmar o commit instalado em health e a configuração das duas bases
   persistentes activas. Não usar o botão de actualizar a API para esta operação.
2. Carregar o JSON aprovado e indicar o SHA-256 esperado, como na Phase 4H.
   O painel não carrega inventários, bases ou arquivos de aquisição para produção.
3. «Verificar condições de publicação» mostra ambas as bases e WAL em bytes,
   disponibilidade de leitura SQLite, escrita da base/pasta para journal, ensaio
   de escrita nas pastas privadas, espaço real disponível no filesystem dos
   backups, espaço necessário para o próximo backup, estado da flag e último
   backup. Não devolve caminhos ou segredos. O estado available do backup significa
   que manifest/tamanhos estão disponíveis, não que a recuperação foi testada.
4. Confirmar também quota do utilizador no cPanel: espaço real do filesystem não
   comprova quota por conta, e quota global não substitui espaço real. O cálculo
   automático exige `3×D + S + 64 MiB` livres antes de cada backup, D=duas bases+WAL,
   S=snapshots JSON. Reservar ainda uma cópia completa para recuperação e retenção.
   Cada base+WAL deve ser <=256 MiB. SQLite >=3.24, filesystem Linux local com
   flock/SQLite fiável; worker com tempo suficiente para backup e transacção.
5. Criar backup pelo botão existente e confirmar available/integrity ok nas duas
   bases. Guardar ID e prova operacional; conservar cópia externa privada. Evitar
   writers/importadores concorrentes na janela; não activar schedules.
6. «Testar recuperação»: confirmar o ensaio isolado do último backup. O servidor
   verifica checksums, integridade SQLite e cópia completa de ambas as bases e
   snapshots, exclusivamente numa pasta temporária privada. Nunca troca bases
   activas ou configuração. Mostrar ID, resultado e impedimentos. Uma falha não
   mantém aprovação anterior. Testar não activa publicação.
7. A aprovação do ensaio vale 30 minutos, só para aquele backup/manifest e os
   mesmos ficheiros. Novo backup, alteração dos ficheiros ou expiração exigem
   novo ensaio. Temporários normais são removidos no fim, incluindo em falhas e
   timeout. Um processo interrompido por SIGKILL pode deixar uma pasta órfã:
   não certifica recuperação; pastas com mais de uma hora são limpas no próximo
   ensaio sob lock. Órfãos recentes ou mais de quatro bloqueiam o ensaio e exigem
   avaliação do operador. Não há limpeza automática de backups definitivos.
8. Activar publicação **manualmente**, apenas na janela autorizada: cPanel →
   Setup Python App → aplicação EarnWage → Environment variables. Definir
   `EARNWAGE_BULK_PUBLICATION_ENABLED` com o valor exacto `true`, guardar e, se o
   alojamento exigir, reiniciar apenas a aplicação Passenger. Confirmar health e
   commit. Não alterar token, caminhos das bases ou EARNWAGE_DEPLOY_ENABLED.
9. Repetir «Verificar condições» e «Pré-visualizar publicação». A revisão vale
   cinco minutos e fica associada ao checksum e estado das duas bases/WAL; edição
   do checksum/ficheiro, alteração das bases ou expiração invalida a revisão.
   Não são aceites conflitos, duplicados ou zero linhas novas para nova escrita.
10. Primeiro pacote BLS/EUA/software_developer/SOC2018:15-1252/nacional/May 2021:

    `dbf36d12a63427e77a4d60d076bd55ef844faa5bd47bd5bc3d4ec67e886f60c9`

    São 12 medidas/uma linha. Embora o operador já tenha obtido 1/0/0, **repetir
    o preview actual** e exigir 1 novo, 0 duplicados e 0 protegidos. Se diferir,
    parar, rever inventário/pacote e autorização; não alterar valores para forçar
    aprovação. Esta entrega não repete o preview nem publica em produção.
11. «Publicar pacote autorizado» fica desactivado até os controlos anteriores
    estarem válidos. Rever checksum e contagens; na confirmação escrever o SHA-256
    exacto apresentado. Esta confirmação autoriza apenas esse pacote. O servidor
    repete os gates, cria backup fresco imediatamente antes da escrita e verifica
    conflitos sob BEGIN IMMEDIATE; conflitos/duplicados detectados na transacção
    recusam a operação integralmente. Nunca actualiza linhas salariais existentes.
12. Exigir published, checksum, contagens e backup_id; validar o histórico na API
    `/v1/us/oews/wages/15-1252?year=2021&area=99` e preservar períodos/unidades/fontes.
    Desactivar a flag ao terminar: remover a variável ou definir `false`, guardar
    e reiniciar Passenger se necessário. Reconfirmar health e condição desactivada.

## Reversão separada

Reverter exige autorização própria. Verificar espaço/permissões, activar manualmente
apenas na janela aprovada e testar a recuperação do **último** backup — a publicação
criou outro backup e invalidou a prova anterior. Seleccionar o checksum publicado,
verificar condições, usar «Reverter pacote publicado» e escrever exactamente
`REVERTER <SHA-256>` na confirmação. Não requer preview de inserção: utiliza o journal
existente. Cria backup fresco e remove apenas linhas inseridas por aquele pacote
que permaneçam integralmente inalteradas. Edição/ausência de linha faz recusar todo
o rollback; não correr VACUUM na janela, pois o journal utiliza rowid.

Exigir rolled_back e contagem esperada; desactivar a flag e preservar as provas.
Se o rollback recusar, parar. Recuperação completa usa cópias novas pelo mecanismo
existente; substituir bases activas exige manutenção e autorização separadas.

Uma resposta perdida, timeout ou erro depois do commit não prova ausência de escrita.
Não repetir automaticamente, não modificar JSON/checksum e não publicar outro pacote
para contornar. Rever o estado pelo operador. Reenvio de pacote já journalizado pode
responder already_published/already_rolled_back sem nova escrita; não é nova aquisição.

## Segurança e limites

Novos POST autenticados: `publication-conditions` (corpo `{}`) e `recovery-test`
(`{"confirm":"test_isolated_backup_recovery"}`). Reutilizam origem HTTPS, token,
limite administrativo de 1 KiB e lock entre workers. Publicação/rollback continuam
nos endpoints existentes com checksum e confirmações específicas. Gates no servidor
impedem contornar o painel. Flag ausente/qualquer valor diferente de `true` bloqueia
escrita, mas permite verificar condições, recuperar isoladamente e pré-visualizar.

Pastas 0700, ficheiros 0600, fora de public_html, sem symlinks. Provas de recuperação
/revisão ficam privadas; não são autorização automática. O ensaio corre no Python
real do Passenger, em subprocesso terminado aos 30 segundos, com memória limitada a
256 MiB. Máximo duas bases de 256 MiB e 100 MiB de snapshots/200 entradas no backup;
reserva de 64 MiB além da cópia. Nunca solicita paths, SQL ou comandos do browser.
Erros devolvem mensagens seguras sem stack traces, output do subprocesso ou segredos.
Os dois backups SQLite são consistentes individualmente, não um snapshot atómico
conjunto: a janela sem writers permanece um requisito operacional.

O arquivo de deployment actual inclui app/publication_control.py através da allow-list
existente. Não altera workflows, scripts de instalação, token, arquivos privados,
datasets, aquisições ou schedules. Testes usam o comando real do workflow, extraem o
arquivo em root isolado e exercitam Passenger, backup, ensaio, publish, rollback e
recuperação; nenhuma base de produção é aberta.
