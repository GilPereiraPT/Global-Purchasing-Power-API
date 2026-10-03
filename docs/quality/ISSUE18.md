# #18 — contabilização salarial dos EUA

O inventário lia north_america_wages (10 profissões dos EUA no export autorizado),
mas não us_oews. O export de 3/10/2026 contém 28 códigos SOC nacionais aprovados,
correspondentes a 29 IDs: accountant e auditor partilham SOC2018 13-2011.

Antes, uma profissão só em us_oews era not_imported. Depois é available com
source BLS_OEWS e período original (May YYYY). Uma profissão em ambas as tabelas
continua um único par país/profissão, com duas proveniências. Contagens BLS físicas
não são multiplicadas por aliases. Contagens por fonte são linhas armazenadas;
não equivalem a células estatísticas independentes somadas entre tabelas.

A contabilização BLS abrange nacional (99/tipo 1), detailed, indústria 000000,
propriedade 1235, mappings existentes e pelo menos uma medida observada. Estados,
grupos amplos, linhas sem salários e tabelas ausentes não inventam cobertura.
_wages executa só SELECT; não cria tabelas, carrega snapshots ou importa salários.
O lifecycle de inicialização da API e das bases económicas permanece existente.

Reprodução com inventário privado autorizado, sem produção: 10 IDs na tabela
norte-americana; 28 SOC/29 IDs na BLS. Não se assume que o snapshot representa o
estado actual após publicações posteriores. Não se modifica qualquer salário.
