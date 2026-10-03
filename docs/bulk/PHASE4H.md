# Phase 4H — carregar e pré-visualizar pelo Data Manager

A secção «Publicação salarial» permite seleccionar o JSON privado já validado,
introduzir o SHA-256 esperado, carregar o pacote e pré-visualizá-lo. Mantém todos
os controlos existentes. Não há botão de publicação ou rollback nesta secção.
O carregamento e preview não autorizam o pacote, não criam backups, não importam
salários e nunca alteram variáveis, tokens ou schedules.

## Procedimento do operador

1. Esta funcionalidade requer uma futura instalação da versão aprovada. Esta PR
   não instala nada. Confirmar health/commit instalado e abrir o Data Manager
   existente, por HTTPS, usando o token existente no campo próprio. Não o copiar
   para a consola, ficheiros ou relatórios.
2. Na secção «Publicação salarial», seleccionar apenas o JSON canónico entregue
   privadamente. Introduzir o checksum esperado recebido separadamente. Máximo
   2 MiB; a extensão é `.json`. O browser verifica o hash antes de transmitir.
3. Carregar. O servidor autentica antes de ler o ficheiro e repete SHA-256,
   limites, validação de JSON/esquema, unicidade, projecção e fontes/classificações
   suportadas. A resposta apresenta checksum, medidas e linhas de destino.
   Um ficheiro inválido é recusado e não fica disponível para preview.
4. Um pacote já existente não é substituído, mesmo sendo idêntico: usar o seu
   checksum e pré-visualizar. Não editar o JSON nem mudar checksum para contornar
   um erro. Os pacotes ficam privados, sem URL pública ou endpoint de download.
5. «Pré-visualizar publicação» lê a base salarial efectiva sem inicializar ou
   migrar tabelas. Mostrar/rever checksum, novos, duplicados e protegidos. O
   preview funciona com publicação desactivada; não é uma autorização.
6. Primeiro pacote: BLS, EUA, software_developer, SOC2018:15-1252, May 2021,
   nacional, 12 medidas/uma linha; 9 182 bytes; SHA-256:

   `dbf36d12a63427e77a4d60d076bd55ef844faa5bd47bd5bc3d4ec67e886f60c9`

   Exigir **1 novo, 0 duplicados, 0 protegidos**. Este resultado foi confirmado
   apenas em ambiente isolado baseado no inventário autorizado. O operador deve
   confirmá-lo em produção após instalação futura; não está garantido por este
   relatório. Se diferir, parar, obter novo inventário e rever o pacote.
7. Consultar o estado/backup nas secções existentes. O preview lista cópias e
   pré-requisitos de configuração, mas não certifica espaço, permissões ou
   recuperação. A indicação `recovery_verified=false` é deliberada: a existência
   de um manifest não demonstra recuperação funcional.
8. Antes de qualquer futura autorização de escrita: confirmar ambas as bases
   persistentes e distintas, cada base+WAL <=256 MiB, SQLite >=3.24 no Passenger,
   filesystem Linux local com flock/SQLite, permissões de leitura/escrita e
   criação de journal/WAL/SHM. Medir quota cPanel e espaço livre: pelo menos
   `3×D + S + 64 MiB` antes de cada backup, D=ambas as bases+WAL, S=snapshots JSON;
   reservar ainda D+S para recuperação e retenção das cópias. Não confundir a
   reserva de upload (64 MiB+pacote) com espaço suficiente para backup.
9. Usar o botão existente «Criar e verificar cópia de segurança»; exigir resultado
   available/integrity ok nas duas bases. Guardar ID, manifest, hashes e cópia
   externa privada. Ensaiar restauração numa pasta nova isolada com o mecanismo
   existente, sem substituir bases/configuração activas. Este ensaio ainda não
   tem controlo browser: o responsável pelo hosting deve atestá-lo. O fluxo de
   carregamento/preview não exige terminal nem gestor de ficheiros.
10. Publicação permanece desactivada por defeito. Revisão e autorização explícita
    devem identificar cada checksum e janela, condicionadas ao preview actual e
    backup/recuperação. O procedimento futuro de publicação/rollback está em
    [PUBLICATION.md](PUBLICATION.md); esta fase não acrescenta controlos de escrita
    nem activa a flag `EARNWAGE_BULK_PUBLICATION_ENABLED`.

## Segurança, limites e retenção

POST `/v1/admin/data-manager/salary-upload`: corpo JSON canónico original,
Content-Type application/json, Content-Length entre 1 e 2 MiB, token no header
existente e SHA esperado em `X-EarnWage-Package-SHA256`. CORS permite apenas a
origem existente. GET é recusado. Respostas não revelam caminhos privados ou
credenciais. Nenhum nome/caminho/SQL/URL de destino fornecido pelo cliente.

A pasta fixa `_earnwage_backups/bulk-packages` é privada 0700, ficheiros 0600,
fora de public_html e sem symlinks. Lock partilhado entre workers, ficheiro
provisório com limpeza em falhas e criação atómica exclusiva impedem sobrescrita
ou exposição de ficheiros incompletos. Máximo 20 entradas (incluindo provisórios
órfãos), 2 MiB por pacote, reserva de 64 MiB. SIGKILL pode deixar um provisório;
este não é aceite nem publicável e conta para o limite. Não há aquisição remota.

Não apagar automaticamente pacotes revistos ou associados ao journal: conservar
com a autorização e provas durante a janela de recuperação; limpeza manual
controlada pelo responsável, sem remover pacotes necessários a rollback/auditoria.
Esta fase não cria outro interface de gestão nem uma tarefa agendada de limpeza.

O arquivo WSGI usa a allow-list actual de app/*.py: inclui o novo módulo sem
alterar deployment. Exclui interface/docs, pacotes privados, inventários, staging,
arquivos de aquisição, bases e configuração. Testes extraem o arquivo construído
pelo próprio comando do workflow e executam passenger_wsgi em root isolado.

## Validação e pendentes

Testes abrangem autenticação antes da leitura, CORS/métodos, formato/hash/tamanho,
truncagem, chaves duplicadas, supressão, duplicados, concorrência, substituições,
symlinks, pasta pública/permissões, falta de espaço, limites, falhas/interrupções,
preview sem activar publicação, browser e WSGI empacotado. O pacote real é mantido
fora do Git; o ensaio exacto usa-o apenas localmente, contra modelo isolado do
inventário. Não são adicionados salários de produção às fixtures.

Pendentes: revisão/merge e instalação futuros por processo separado; preview
real em produção e atestação dos pré-requisitos operacionais. Não se fez merge,
deployment, publicação ou pedido administrativo à produção nesta fase.
