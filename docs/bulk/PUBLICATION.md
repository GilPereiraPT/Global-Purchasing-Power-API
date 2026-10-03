# Publicação controlada de salários — Phase 4C

Nenhuma aquisição, transferência, merge ou publicação produtiva é executada por
esta entrega. O código fica desactivado por omissão. Só os ensaios usam bases
locais isoladas; não existe acesso directo à base produtiva.

## Preparação offline

Reutilizar o staging e os artefactos Phase 4B; não voltar a descarregar os datasets.

```bash
python -m scripts.bulk_publication_package \
  --staging /ABSOLUTO/PRIVADO/staging.sqlite3 \
  --output /ABSOLUTO/PRIVADO/novos-pacotes --limit 1000
```

A saída contém um índice e ficheiros JSON nomeados pelo SHA-256 do conteúdo exacto.
O directório deve ser novo e privado. Só `bulk_current` com versão `accepted`,
artefacto registado e último run completo pode entrar. Supressões/quarentena não
são transformadas em zero. Cada pacote tem até 1 000 observações e 2 MiB; medidas
da mesma linha OEWS ficam juntas. A selecção offline está limitada a 20 000 células
nacionais/provinciais em memória; os restantes âmbitos são contados em SQL.
O checksum garante integridade, não certifica por si só a origem: o operador deve
rever o índice, a proveniência oficial e a exportação produtiva autorizada.

## Âmbito representável sem alterar contratos existentes

| Origem | Âmbito inicial | Modelo existente |
| --- | --- | --- |
| BLS SOC 2018, 2021–2025 | Nacional, 12 medidas publicadas | `us_oews` |
| Job Bank NOC 2021, release 2025 | Nacional, média/mediana | `north_america_wages` |
| Job Bank NOC 2021, release 2025 | Totais provinciais/territoriais, seis medidas | `ca_province_wages` |

As regiões económicas canadenses não têm tabela/API existente equivalente.
As versões históricas BLS do staging não guardam `prim_state` original; não se
infere este identificador. A publicação regional BLS requer completar metadados
com os arquivos já adquiridos e validar o âmbito exacto. Estas observações
continuam no staging, sem substituição por salários nacionais/provinciais.
Não se convertem unidades, períodos plurianuais ou intervalos em médias.
Títulos dos alvos usam o registo oficial de mapeamentos já revisto; não se criam
novas correspondências. Valores não representáveis exactamente na passagem para
o schema `REAL` existente são recusados; o pacote preserva o valor decimal original.

## Autorização através do Data Manager existente

Pré-requisitos manuais para uma futura publicação, depois da revisão e integração:

1. Obter uma **exportação produtiva autorizada**, compará-la em modo read-only e
   rever o pacote e seu checksum. Não assumir que a baseline Git é produção.
2. Configurar os caminhos absolutos persistentes existentes `GPP_CACHE_DB` e
   `EARNWAGE_INSIGHTS_DB`; preservar bases, ficheiros `.env` e token administrativo.
3. Confirmar permissões, espaço para backups privados e recuperação. Cada base,
   incluindo WAL, fica limitada a 256 MiB nesta via de publicação. Bases maiores
   precisam de um procedimento operacional revisto, não de contornar o limite.
4. Colocar **apenas** os pacotes seleccionados em
   `_earnwage_backups/bulk-packages/<sha256>.json`, fora de `public_html`;
   directório 0700 e ficheiros 0600. Não copiar os ZIP/CSV/SQLite de aquisição.
5. Activar manualmente `EARNWAGE_BULK_PUBLICATION_ENABLED=true`. Não activar cron,
   SSH nem alterar `EARNWAGE_DEPLOY_ENABLED` por causa desta publicação.
6. Usar o token existente no header `X-EarnWage-Admin-Token`, em HTTPS, sem o
   escrever em argumentos, ficheiros de relatório ou logs. Não criar um novo token.

POST `/v1/admin/data-manager/bulk-preview` recebe `{"checksum":"<64 hex>"}`.
O preview não escreve: mostra linhas novas, duplicadas e existentes protegidas.
POST `/v1/admin/data-manager/bulk-publish` requer também
`"confirm":"publish_reviewed_salary_package"`.
A autenticação, origem CORS, tamanho do pedido e lock são os do Data Manager.
É criado um **backup novo de ambas as bases** antes de cada tentativa de escrita.
O schema/PK são verificados e o plano é repetido sob `BEGIN IMMEDIATE`, com espera
máxima de 5 segundos pelo lock SQLite. Não existe `INSERT OR REPLACE`, `UPDATE` de
salários existentes ou SQL fornecido pelo cliente. Conflitos e células existentes
NULL são protegidos; não se completam implicitamente linhas já validadas.
Os pedidos de publicação idempotentes devolvem `already_published`.

## Rollback e recuperação

POST `/v1/admin/data-manager/bulk-rollback` requer o checksum e
`"confirm":"rollback_reviewed_salary_package"`. Faz backup fresco antes de remover
apenas as linhas inseridas por esse pacote. Compara a linha completa com o journal;
se houver edição posterior ou linha ausente, recusa toda a transacção e pede
recuperação manual. Dados existentes/duplicados/conflituantes nunca entram no
journal de remoção. A publicação revertida não se reaplica automaticamente:
preparar uma nova operação revista, em vez de contornar `already_rolled_back`.

Em caso de falha, o journal e a transacção impedem importações parciais. Para
recuperação completa reutilizar a ferramenta existente:

```bash
python -m scripts.restore_earnwage_data \
  --backup /ABSOLUTO/PRIVADO/backup-... \
  --output /ABSOLUTO/PRIVADO/nova-recuperacao
```

Os checksums e a integridade SQLite são verificados. A recuperação cria cópias
novas; não troca bases activas nem variáveis. Uma futura troca deve ser manual,
com aplicação parada e protecção contra escritas concorrentes. Se a escrita salarial
já tiver sido confirmada mas falhar o log económico, o pedido pode devolver erro;
o checksum/journal permite consultar preview e repetir sem duplicar salários.

Os endpoints são administrativos WSGI do Data Manager, tal como os anteriores;
a API pública FastAPI/WSGI e os respectivos contratos salariais ficam intactos.
