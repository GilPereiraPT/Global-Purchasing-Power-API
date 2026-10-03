# #19 — frescura cambial

A cache ECB é on-demand, com TTL 24 h. O inventário lê a cache sem actualizar:
expired/not_cached não demonstram falha da conversão; um pedido live tenta obter
nova observação. Não há cron de câmbios nem se adiciona nesta PR.

A falha confirmada era validar só fetched_at: uma resposta recente contendo
TIME_PERIOD antigo podia ser guardada/servida como disponível. Agora tanto cache
como resposta devem ter moeda/dimensões ECB corretas, número finito positivo,
data ISO não futura e idade <=7 dias de calendário. Este limite operacional
explícito permite fins de semana/feriados; não significa cotação intradiária e
não altera a data original. A resposta continua a expor period e unidade por EUR.
Frequência D, denominador EUR, SP00 e sufixo A são obrigatórios no CSV upstream.

Refresh limitado a uma resposta/25 s/64 KiB. Falhas, estruturas inesperadas,
valores inválidos e datas antigas falham fechadas; não há fallback stale, taxa
inventada ou novo fornecedor. Timestamps futuros da cache são também rejeitados.
PKR não pertence às referências actuais ECB: unavailable, mesmo existindo um
valor antigo na cache. Não se liga outro serviço sem licença/fonte validadas.

Fontes oficiais:
- https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html
- https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&lastNObservations=1

Verificação independente em 3/10/2026: ECB HTTP200, USD 1.1225 por EUR, observação
2026-10-02, dimensões D/USD/EUR/SP00/A. É evidência datada, não fixture permanente.
O inventário distingue expired (TTL), invalid_or_stale_observation (valor/data)
e unsupported (moeda sem série). Isto não implica uma tentativa live fracassada.

O /v1/earnwage/compare actualmente não converte salários: currency_conversion é
not_requested e refere o endpoint live separado; não produz poder de compra líquido.
A PR não introduz conversão, scraping, agendamentos nem alterações à produção.
