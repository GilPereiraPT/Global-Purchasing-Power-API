# EarnWage — GitHub Pages (publicação do website)

> **Estado:** configuração preparada num ramo/PR. A mera abertura da PR não publica o novo website. Não executar deploy nem merge sem autorização.

## Destino

- Repositório: `GilPereiraPT/Global-Purchasing-Power-API`.
- GitHub Pages: `https://gilpereirapt.github.io/Global-Purchasing-Power-API/` (endereço previsto do repositório; confirmar em **Settings → Pages → Visit site**).
- **Homepage**: os 15 ficheiros HTML do diretório `website/`, publicados na raiz do Pages.
- **Laboratório técnico antigo**: todo o conteúdo de `docs/` é mantido em **`/lab/`**, com entrada em `/lab/index.html`.
- Workflow único: `.github/workflows/earnwage-lab-pages.yml` no ramo `main`. Faz a montagem `website → _site/`, `docs → _site/lab/`, valida scripts e publica o artefacto com GitHub Actions.
- Ativação: repositório → **Settings → Pages → Build and deployment → Source: GitHub Actions**. O repositório já contém um workflow de Pages; confirmar a configuração antes da publicação.
- O workflow corre num `push` para `main` que afete o website, os docs ou o próprio workflow, e tem `workflow_dispatch` manual. Uma PR isolada não publica automaticamente.
- Não configurar domínio personalizado, DNS, Cloudflare Pages ou Pages Functions nesta fase.

## API existente

- O endereço da API permanece em **`website/api-config.js`**:
  `https://earnwage-api.policlinicosdesantoandre.com`.
- A origem do browser GitHub Pages é **`https://gilpereirapt.github.io`** (sem o caminho do repositório).
- O adaptador CORS em `app/web_cors.py` já inclui esta origem como `LEGACY_ORIGIN`. Verificar no browser que o **servidor efetivamente instalado** também permite esta origem. O GitHub Pages não instala alterações da API; a versão pública pode diferir da branch.
- Confirmar os endpoints públicos `/v1/countries`, `/v1/occupations`, `/v1/earnwage/overview`, `/v1/economy/coverage` e os recursos históricos. Não ativar CORS administrativo nem usar o wildcard `*`.
- Os cenários PPP da PR #47 e fiscais da #48 continuam pendentes no backend; o website deve identificar funções não disponíveis sem fabricar valores.

## Funcionalidades estáticas e limitações

- Homepage, comparação, salários, países, profissões, fontes, histórico e guias são HTML/JS/CSS estáticos; as consultas dinâmicas são feitas por HTTPS à API pública.
- O **formulário** em `about.html` continua desativado. GitHub Pages **não executa `POST /api/report`**, nem as funções em `functions/`; não publicar mensagens de sucesso nem sugerir que recebe emails.
- O ficheiro `website/_headers` pertence a outra plataforma e **não configura cabeçalhos HTTP no GitHub Pages**. É excluído do artefacto.
- O ficheiro `.nojekyll` é colocado na raiz do artefacto para evitar processamento Jekyll inesperado.
- São preservados o domínio da API, os dados importados, a BD de produção, os workflows de importação e a aplicação Android.

## Checklist antes da publicação

- [ ] PRs #49, #50, #51, #52 e #53 aprovadas, integradas pela ordem das dependências; PR GitHub Pages integrada depois destas
- [ ] CI verde e validação de HTML, JavaScript e recursos locais no workflow
- [ ] Página inicial do EarnWage abre na raiz do GitHub Pages
- [ ] Laboratório técnico abre em `/lab/`, sem substituir os seus ficheiros
- [ ] Desktop e Android: navegação, pesquisa, menus, seletores, sete idiomas
- [ ] API e CORS: confirmar resultados reais e estados de indisponibilidade sem erros na consola
- [ ] Testar uma profissão com dados, outra sem dados, escolha estadual/provincial e uma comparação
- [ ] Formulário de feedback permanece desativado, sem promessas de entrega
- [ ] Links, acessibilidade, SEO e separação entre dados brutos, líquidos e médias de grupos validados
