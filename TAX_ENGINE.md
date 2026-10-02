# Motor de salário líquido — Fase 3

## Estado da entrega

A infraestrutura do motor anual, a API versionada e a integração opcional no
EarnWage estão implementadas. **O cálculo português continua indisponível.**
Não foi possível consultar a legislação oficial neste ambiente: o proxy devolveu
`CONNECT tunnel failed, response 403` ao aceder ao Portal das Finanças. Não há
qualquer ano fiscal português validado ou taxa portuguesa ativa nesta entrega.
2025 é apenas um ano candidato à primeira validação; não é um ano suportado.

A ausência de cálculo é intencional. A existência de URLs oficiais ou o sucesso
dos testes de aritmética não valida uma regra fiscal. Não foram usados valores
lembrados, simuladores de terceiros ou tabelas de retenção como substitutos da
legislação anual.

## Arquitetura

- `app/tax_engine.py`: pedidos imutáveis, protocolo de adaptadores nacionais,
  registo de países, validação partilhada, aritmética progressiva e apresentação.
- `app/tax_portugal.py`: cenário inicial, pressupostos, lacunas e fontes a
  consultar. O adaptador devolve exclusivamente `unavailable`.
- `app/main.py` e `app/native_wsgi.py`: os mesmos serviços e validação de cálculo
  nos runtimes de desenvolvimento e produção.
- `app/earnwage_queries.py`: seleção explícita do novo cenário, sem aplicar
  impostos automaticamente aos salários estatísticos existentes.

Os módulos são ficheiros diretos de `app/`, compatíveis com o empacotamento
existente. Não foi alterado o sistema de deployment.

Cada adaptador recebe país, ano fiscal, rendimento bruto anual, cenário e região
opcional. Tem de verificar as regras nacionais e regionais aplicáveis ao pedido.
Não há fallback automático de região, ano ou situação familiar. Para Portugal é
necessária a região explícita `mainland`.

Os estados do novo contrato são:

| Estado | Significado | Líquido anual / equivalente mensal |
| --- | --- | --- |
| `verified` | Modelo completo e validado para o cenário e ano selecionados | Disponíveis |
| `partial` | Existem componentes, mas faltam regras ou componentes necessários | `null` |
| `unavailable` | Não existe cálculo validado para o pedido | `null` |

O motor impede a apresentação de líquido se um adaptador declarar `verified`
sem imposto anual, contribuições, moeda, fontes ou regras aplicáveis. O estado
`verified` descreve a validação do modelo dentro do seu âmbito; o resultado é
uma estimativa anual, não uma liquidação da AT.

Todos os cálculos monetários usam `Decimal`. A nova API representa os montantes
como **strings decimais com duas casas**, por exemplo `"30000.01"`; valores
indisponíveis são `null`. O bruto deve ser positivo, ter no máximo duas casas
decimais e não exceder 100 000 000. Não são aceites NaN, infinito, parâmetros de
cálculo inesperados ou parâmetros duplicados.

A apresentação genérica usa `ROUND_HALF_UP`. As regras de arredondamento legal,
deduções, abatimentos e créditos pertencem ao adaptador e terão de ser validadas
antes da sua ativação. Não se presume que o algoritmo progressivo genérico,
isoladamente, reproduza a liquidação portuguesa.

## Primeiro cenário português proposto

Identificador: `single_employee_no_dependents`.

- Residente fiscal durante todo o ano em Portugal continental.
- Adulto solteiro, sem dependentes e sem deficiência.
- Apenas rendimentos de trabalho dependente da categoria A.
- Regime geral da Segurança Social; bruto integralmente sujeito a contribuições.
- Sem IRS Jovem, RNH, IFICI ou outros regimes especiais.
- Sem outros rendimentos, deduções opcionais ou créditos por despesas reclamados.

Este âmbito ainda precisa de validação. Não são assumidos a zero benefícios,
abatimentos ou ajustes obrigatórios. Casados, dependentes, ilhas e regimes
especiais não estão implementados. Não são calculadas contribuições patronais,
retenção mensal, reembolso/acerto com retenções ou pagamentos efetivos em 12/14
meses.

O objetivo de `income_tax` é uma estimativa do **IRS final anual**, que será
subtraída, juntamente com as contribuições do trabalhador, ao bruto anual.
`monthly_equivalent_12` será o líquido anual dividido por 12; não representa um
recibo de vencimento, subsídios de férias/Natal nem retenção na fonte.

### Regras em falta antes de ativar Portugal

1. Tabela anual de escalões e taxas e alterações legislativas do ano selecionado.
2. Dedução específica da categoria A e interação com contribuições obrigatórias.
3. Mínimo de existência: limiares, fórmulas e limites de aplicação.
4. Taxa adicional de solidariedade e interação com deduções.
5. Ajustes obrigatórios à coleta, créditos aplicáveis e arredondamento anual.
6. Taxa contributiva do trabalhador, base de incidência e exceções do regime geral.

As fontes a consultar são a [Autoridade Tributária](https://info.portaldasfinancas.gov.pt/),
o [Diário da República](https://diariodarepublica.pt/) e a
[Segurança Social](https://www.seg-social.pt/). Os links em `source_candidates`
são candidatos não verificados, não proveniência de um cálculo. As páginas de
legislação consolidada atual não bastam para provar as regras históricas de 2025.

Para ativar um ano será necessário registar o URL oficial efetivamente
verificado, ano fiscal, versão/alterações legislativas, artigos e regras
aplicáveis, bem como verificar a fórmula completa contra exemplos oficiais ou
casos independentemente calculados. Só então poderá ser adicionado a
`supported_tax_years` e o respetivo cenário passar a `verified`.

## API versionada — FastAPI e WSGI

| Método e caminho | Função |
| --- | --- |
| `GET /v1/tax/countries` | Adaptadores, cenários e países efetivamente disponíveis |
| `GET /v1/tax/years/{country}` | Anos fiscais suportados |
| `GET /v1/tax/assumptions/{country}` | Pressupostos, limitações, lacunas e fontes candidatas |
| `GET /v1/tax/calculate` | Pedido anual explícito |

Exemplo válido, com resultado atualmente indisponível:

```text
/v1/tax/calculate?country=PT&annual_gross=30000.01&tax_year=2025&scenario=single_employee_no_dependents&region=mainland
```

Excerto da resposta:

```json
{
  "status": "unavailable",
  "country": "PT",
  "currency": "EUR",
  "tax_year": 2025,
  "annual_gross": "30000.01",
  "income_tax": null,
  "employee_social_security": null,
  "net_income": null,
  "monthly_equivalent_12": null,
  "sources": [],
  "applicable_rules": []
}
```

`country`, `annual_gross`, `tax_year` e `scenario` são obrigatórios. A região é
opcional no protocolo internacional, mas necessária para o cenário continental
português. Entradas inválidas recebem HTTP 422; países, anos, regiões e cenários
sem modelo validado recebem HTTP 200 com `status: unavailable`, montantes nulos e
motivo explícito. Isto distingue um pedido inválido de falta de cobertura fiscal.

Atualmente `available_countries` e `supported_tax_years` estão vazios. A presença
de Portugal no catálogo de adaptadores não significa que exista cálculo ativo.

### Overview e comparação

Os pedidos existentes mantêm o comportamento e os contratos anteriores. O
endpoint legado `/v1/tax-components/{country}` não foi alterado.

Para selecionar o novo motor no overview:

```text
/v1/earnwage/overview?country=PT&occupation=nurse&annual_gross=30000.01&tax_scenario=single_employee_no_dependents&tax_region=mainland&net_tax_year=2025
```

`tax_scenario`, `tax_region` e `net_tax_year` selecionam o novo modelo.
`net_tax_year` é obrigatório quando há `tax_scenario`: não se reutiliza
silenciosamente o ano por defeito do cenário fiscal legado. O `region` existente
continua a descrever os dados salariais; `tax_region` descreve a jurisdição fiscal.
O bruto é introduzido pelo utilizador; não é inferido do salário da profissão.

Na comparação existem os parâmetros correspondentes com sufixos `_a` e `_b`,
incluindo `annual_gross_a/b` e `net_tax_year_a/b`. Cada país pode usar um ano e
cenário independentes. O resultado está em `country_a.tax_scenario` e
`country_b.tax_scenario`.

Os resultados líquidos só podem aparecer quando o adaptador é integralmente
suportado. `net_purchasing_power` continua indisponível: não foi criado um modelo
de custo de vida nem uma classificação internacional de salários líquidos.

## Validação e configuração necessária

Os testes novos cobrem limites imediatamente abaixo, no valor e acima dos
escalões; arredondamento decimal; entradas inválidas; resultados incompletos;
ano obrigatório; falta de cobertura; paridade FastAPI/WSGI e integração no
overview/comparação. As tabelas e adaptadores verificados dos testes são
**sintéticos**. Não são exemplos portugueses nem provam conformidade fiscal.

Antes da ativação faltam testes portugueses baseados em regras oficiais para
cada escalão, mínimo de existência, dedução específica, solidariedade,
contribuições e arredondamento, além de casos de referência anuais independentes.

Foi preparado um rascunho aditivo da configuração de rede da nuvem, preservando
`api.github.com` e os presets existentes, com os destinos:

- `info.portaldasfinancas.gov.pt`
- `diariodarepublica.pt` e `files.diariodarepublica.pt`
- `www.seg-social.pt` e `www.seg-social.gov.pt`

É necessário guardar essa configuração nas definições do ambiente e confirmar
que as consultas HTTPS às fontes funcionam. Guardar o rascunho por si só não
aplica a configuração à máquina. Não são necessários novos segredos ou mudanças
no deployment para os endpoints novos.

### Resultados desta entrega

Base `main` verificada: `1a57090`, que inclui a Fase 2 e as três correções de dados
anteriores. A suite original passou com **265 aprovados, 0 falhados**.

Suite completa após esta implementação:

```text
.venv/bin/python -m pytest -q
346 passed, 1 warning in 70.57s
```

São **81 testes novos**, 346 aprovados e 0 falhados. O aviso existente
`StarletteDeprecationWarning` refere a utilização de `httpx` no TestClient;
não foram alteradas dependências fora do âmbito. `pip check` não identificou
incompatibilidades. Os testes existentes foram preservados.

A entrega fica numa branch dedicada e em PR de rascunho para revisão. A
infraestrutura está testada, mas o motor fiscal português ainda não está pronto
para utilização em produção. Não houve merge em `main`, deployment, alterações
à aplicação Android, a segredos ou a bases de dados de produção.
