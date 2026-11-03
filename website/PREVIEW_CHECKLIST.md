# EarnWage — checklist de pré-visualização no Cloudflare Pages

> **Estado:** preparado em código; não foi criado nem publicado qualquer projeto Cloudflare, alterado DNS ou executado merge. Não publicar antes de concluir os pontos obrigatórios.

## Configuração da pré-visualização (não de produção)

- Repositório: `GilPereiraPT/Global-Purchasing-Power-API`
- Branch de desenvolvimento: `feature/earnwage-public-website` (PR #49)
- Diretório raiz do projeto Cloudflare Pages: **raiz do repositório**
- Comando de build: **nenhum** (site HTML/CSS/JS estático)
- Diretório de saída: **`website`**
- Diretório de Pages Functions: **`functions/`** na raiz do repositório
- Primeiro verificar o endereço de pré-visualização `https://<preview-exato>.pages.dev`. Não substituir o domínio público nem configurar DNS de produção nesta etapa.

## Ligação à API — configuração necessária antes dos testes

- O frontend usa **`website/api-config.js`** com a API pública existente.
- A API deve receber a variável **`EARNWAGE_PUBLIC_CORS_ORIGINS`** com o(s) endereço(s) HTTPS **exato(s)** de pré-visualização, separados por vírgulas; por exemplo, `https://earnwage-preview.pages.dev` (exemplo ilustrativo, não um endereço confirmado).
- Esta autorização só será aplicada quando o código de CORS da PR for revisto e disponibilizado no servidor; adicionar uma variável de ambiente, por si só, não altera o servidor atual.
- CORS permite exclusivamente origens HTTPS explícitas; não usar `*`, subdomínios genéricos ou `http://`.
- A alteração apenas permite ler as rotas públicas por `GET/HEAD`; **não** autoriza operações administrativas nem atualizações de dados.
- Confirmar pelo DevTools do navegador que `/v1/countries`, `/v1/occupations`, `/v1/earnwage/overview`, `/v1/economy/coverage` e a nova rota de histórico devolvem respostas válidas sem erros de CORS. Conferir disponibilidade de dados e diferenças entre a API publicada e a branch em desenvolvimento.

## Formulário About (continua desativado até configuração)

- Configurar `REPORT_TO_EMAIL` como o endereço de receção acordado, apenas nas variáveis privadas do Pages.
- Configurar o remetente autorizado `REPORT_FROM_EMAIL`, `RESEND_API_KEY`, `TURNSTILE_SECRET_KEY` e `REPORT_ALLOWED_ORIGIN` (origem HTTPS exata da pré-visualização).
- Adicionar apenas a chave **pública** de Turnstile ao ficheiro `website/report-config.js`.
- Configurar um limite de pedidos no Cloudflare WAF para `/api/report`, verificar a entrega dos emails com assunto `EarnWage: ...` e o endereço Reply-To.
- Confirmar a informação de privacidade, retenção dos dados e prestador de email antes de disponibilizar o formulário.
- Até lá, o botão de envio permanece desativado; não alterar essa salvaguarda.

## Testes funcionais obrigatórios

- [ ] Desktop (Chrome e Edge): menus, links, resultados, focus visível e legibilidade
- [ ] Android e largura 360 px: menu `Mais`, barra de navegação, seletor de idioma e formulários sem cortes
- [ ] Teclado: `Tab`, `Enter`, `Escape`, ligação `Saltar para o conteúdo` e foco em links
- [ ] Primeira visita: idioma do navegador se suportado; caso contrário inglês
- [ ] Mudança manual para todos os sete idiomas; preservar escolha após recarregar e entre páginas
- [ ] Comparação: salário bruto anual, moeda, país, profissão, cobertura PPP, anos coincidentes e cenários fiscais não inventados
- [ ] Países, salários e emprego: fontes e anos; sem valores estimados apresentados como observações
- [ ] Históricos: anos sem observação não são interpolados; a falta de dados não é representada por zero
- [ ] Grupos profissionais: não confundir estatísticas de grupos com salários individuais
- [ ] Fontes: links externos HTTPS com `rel=noopener noreferrer` e sem URLs de origem duvidosa
- [ ] Formulário: erro de captcha e falha de envio não indicam sucesso
- [ ] Console: sem erros JavaScript, 404 de assets ou avisos de CORS
- [ ] Verificar metadados SEO, títulos, acessibilidade e política de privacidade antes do lançamento

## Critérios para aprovação

1. Os testes automáticos da PR estão verdes.
2. Todos os 15 ficheiros HTML carregam os estilos e scripts partilhados.
3. A API responde corretamente no domínio de pré-visualização através de origens expressamente autorizadas.
4. Falhas, cobertura parcial e limitação de fontes são comunicadas de forma clara.
5. Aprovação explícita para merge, configuração do domínio e lançamento público.

**Não executar deploy nem merge sem autorização.**
