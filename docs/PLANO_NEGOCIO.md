# BacenData — Plano de Negocio e Monetizacao

> Guia passo a passo para transformar o BacenData em um produto SaaS rentavel.
> Escrito para Felipe, fundador solo, 10-20h/semana, projeto paralelo ao emprego.

---

## Indice

1. [Resumo Executivo](#1-resumo-executivo)
2. [Analise de Mercado](#2-analise-de-mercado)
3. [Modelo de Negocio](#3-modelo-de-negocio)
4. [Planos e Precificacao](#4-planos-e-precificacao)
5. [Roadmap de Monetizacao (14 semanas)](#5-roadmap-de-monetizacao-14-semanas)
6. [Passo a Passo: Semana a Semana](#6-passo-a-passo-semana-a-semana)
7. [Infraestrutura e Custos](#7-infraestrutura-e-custos)
8. [Marketing e Aquisicao](#8-marketing-e-aquisicao)
9. [Metricas e KPIs](#9-metricas-e-kpis)
10. [Aspectos Legais](#10-aspectos-legais)
11. [Riscos e Mitigacoes](#11-riscos-e-mitigacoes)
12. [Projecao Financeira](#12-projecao-financeira)

---

## 1. Resumo Executivo

**BacenData** e uma plataforma SaaS que simplifica o acesso a dados publicos do Banco Central do Brasil. O produto resolve uma dor real: desde marco/2025 a API SGS do BACEN limita consultas a 10 anos e exige filtros obrigatorios, tornando penoso o trabalho de analistas, economistas e desenvolvedores.

### O que ja existe (pronto)

- **Wrapper Python** publicado no PyPI (`pip install bacendata`) — v0.1.0
- **API REST** com FastAPI — 6 endpoints, autenticacao, rate limiting
- **73 testes** passando, **88% de cobertura**

### Proposta de valor

| Para quem | Dor | Solucao BacenData |
|-----------|-----|-------------------|
| Desenvolvedores | API do BACEN e complexa e limitada | `pip install bacendata` + API REST simples |
| Economistas | Download manual de series, sem historico longo | Paginacao automatica >10 anos, cache, bulk |
| Fintechs | Dados BACEN em producao sem confiabilidade | API com uptime, retry, cache, SLA |
| Consultorias | Relatorios manuais, sem dashboards | Dashboard pronto com graficos interativos |

### Modelo de receita

**Freemium** com 3 tiers: Free (R$0) -> Pro (R$79/mes) -> Enterprise (R$299/mes)

---

## 2. Analise de Mercado

### Tamanho do mercado (Brasil)

| Segmento | Estimativa | Fonte |
|----------|-----------|-------|
| Fintechs ativas | ~1.500 | ABFintechs |
| Consultorias financeiras | ~3.000 | CVM/ANBIMA |
| Economistas e pesquisadores | ~10.000 | ANPEC/universidades |
| Desenvolvedores que usam dados BACEN | ~50.000 | GitHub/PyPI |

### Mercado enderecavel (SAM)

- **Desenvolvedores** que instalam pacotes Python de dados financeiros: ~5.000
- **Fintechs/consultorias** que precisam de dados BACEN em producao: ~500
- **Ticket medio estimado**: R$100/mes
- **SAM**: R$500.000/mes = R$6M/ano

### Concorrencia

| Concorrente | O que faz | Limitacao |
|------------|-----------|-----------|
| API SGS direta | Dados brutos | Limite 10 anos, sem cache, sem docs |
| python-bcb | Wrapper Python | Nao trata paginacao, sem API REST |
| ipeadata | Dados IPEA | Foco em dados IPEA, nao BACEN SGS |
| Quandl/Refinitiv | Dados financeiros | Caro (US$500+/mes), foco global |
| Economática | Terminal financeiro | R$2.000+/mes, para institucionais |

**Diferencial BacenData**: unico produto que combina wrapper Python gratuito + API REST + paginacao automatica + cache + dashboard, focado 100% no BACEN SGS brasileiro, com precificacao acessivel.

---

## 3. Modelo de Negocio

### Funil de conversao

```
PyPI (wrapper gratis)
    |
    v  [Instala, testa, gosta]
GitHub (stars, issues, contribuicoes)
    |
    v  [Precisa de mais: escala, cache servidor, SLA]
Landing Page (bacendata.com.br)
    |
    v  [Cadastra email]
Free Tier (100 req/dia)
    |
    v  [Atinge limite, precisa de bulk/webhooks]
Pro Tier - R$79/mes
    |
    v  [Empresa, precisa de SLA e suporte]
Enterprise - R$299/mes
```

### Fontes de receita

| Fonte | % da receita | Margem |
|-------|-------------|--------|
| Assinaturas Pro/Enterprise | 70% | ~90% |
| Dashboard premium | 20% | ~90% |
| Consultoria/customizacao | 10% | ~60% |

---

## 4. Planos e Precificacao

### Tabela de planos

| Recurso | Free | Pro (R$79/mes) | Enterprise (R$299/mes) |
|---------|------|----------------|------------------------|
| **Requisicoes/dia** | 100 | 10.000 | Ilimitado |
| **Series do catalogo** | 14 | Todas SGS | Todas SGS + customizadas |
| **Paginacao automatica** | Sim | Sim | Sim |
| **Cache servidor** | Nao | Sim (Redis) | Sim (dedicado) |
| **Bulk (series/req)** | 5 | 20 | 50 |
| **Webhooks/alertas** | Nao | Sim | Sim |
| **Dashboard** | Basico | Completo | Completo + exportacao |
| **Suporte** | GitHub Issues | Email (48h) | Prioritario (4h) |
| **SLA uptime** | Nao | 99.5% | 99.9% |
| **API keys** | 1 | 5 | Ilimitadas |

### Por que esses precos?

- **R$79/mes** e acessivel para profissionais autonomos e pequenas fintechs (< custo de 1h de trabalho de analista)
- **R$299/mes** e irrisorio para empresas que gastam R$2.000+/mes com Economatica ou Bloomberg
- O Free gera volume de usuarios e marketing organico
- Conversao esperada: 2-5% Free -> Pro, 10-20% Pro -> Enterprise

---

## 5. Roadmap de Monetizacao (14 semanas)

### Visao geral das fases

```
Semanas 1-3:   [====] Dashboard Streamlit (Fase 3)
Semanas 4-5:   [====] Landing page + cadastro
Semanas 6-7:   [====] Deploy producao + dominio
Semanas 8-9:   [====] Stripe + sistema de planos
Semanas 10-11: [====] Painel do usuario + API keys
Semanas 12-13: [====] Marketing + lancamento
Semana 14:     [====] Primeiro faturamento
```

---

## 6. Passo a Passo: Semana a Semana

### FASE 3: Dashboard (Semanas 1-3)

---

#### Semana 1: Dashboard MVP com Streamlit

**Objetivo**: Dashboard funcional com graficos interativos das 14 series.

**Dia 1-2: Setup e layout**

1. Criar arquivo `frontend/app.py`
2. Instalar dependencias: `pip install streamlit plotly`
3. Layout com sidebar para selecao de series
4. Titulo, descricao e branding basico

**Dia 3-4: Graficos interativos**

1. Grafico de linha para serie unica (Plotly)
2. Seletor de periodo (predefinidos: 1M, 3M, 6M, 1A, 5A, 10A, MAX)
3. Tabela com dados brutos abaixo do grafico
4. Botao de download CSV/Excel

**Dia 5: Comparacao de series**

1. Selecao de ate 3 series lado a lado
2. Eixo Y duplo para unidades diferentes
3. Grafico de correlacao simples

**Entregavel**: `streamlit run frontend/app.py` funcionando com dados reais.

---

#### Semana 2: Dashboard avancado

**Dia 1-2: Indicadores resumo**

1. Cards com valores atuais (Selic, IPCA, Dolar, Euro)
2. Variacao percentual (dia, mes, ano)
3. Mini-graficos sparkline nos cards

**Dia 3-4: Filtros e customizacao**

1. Filtro de data com calendario
2. Agrupamento (diario, semanal, mensal)
3. Calculo de media movel (7d, 30d, 90d)
4. Opcao de mostrar/esconder legenda e grid

**Dia 5: UX e responsividade**

1. Tema visual consistente (cores do BACEN: azul/dourado)
2. Loading states e mensagens de erro amigaveis
3. Favicon e titulo da aba
4. Testar em diferentes tamanhos de tela

**Entregavel**: Dashboard publicavel com boa aparencia.

---

#### Semana 3: Polimento e deploy do dashboard

**Dia 1-2: Pagina "Sobre" e documentacao inline**

1. Aba "Sobre" explicando o projeto
2. Tooltips nos graficos explicando cada serie
3. Link para a API e wrapper Python

**Dia 3: Deploy do dashboard**

1. Criar conta no Streamlit Community Cloud (gratuito)
2. Configurar `requirements.txt` para o dashboard
3. Deploy via GitHub (push = deploy automatico)
4. Testar URL publica

**Dia 4-5: Testes e feedback**

1. Compartilhar com 5-10 pessoas do mercado financeiro
2. Coletar feedback (Google Forms)
3. Corrigir bugs e ajustes de UX
4. Preparar screenshots para landing page

**Entregavel**: Dashboard publico em `bacendata.streamlit.app`

---

### FASE 4: Monetizacao (Semanas 4-14)

---

#### Semana 4: Landing page

**Objetivo**: Pagina profissional que converte visitantes em cadastros.

**Dia 1: Escolher plataforma**

Opcoes (do mais rapido ao mais customizavel):

| Opcao | Custo | Tempo | Recomendacao |
|-------|-------|-------|-------------|
| Carrd.co | $19/ano | 2h | Para MVP rapido |
| Next.js + Vercel | Gratis | 2 dias | Para controle total |
| Framer | $5/mes | 4h | Visual bonito, sem codigo |

**Recomendacao**: Comecar com **Carrd.co** (R$100/ano) para validar, migrar para Next.js quando escalar.

**Dia 2-3: Criar a landing page**

Estrutura da pagina:

```
1. Hero: "Dados do Banco Central em segundos"
   - Subtitulo: API moderna + Dashboard + Python wrapper
   - CTA: "Comecar gratis" / "Ver documentacao"

2. Problema: "A API do BACEN limitou consultas em 2025"
   - Antes: codigo complexo, 10 anos max, sem cache
   - Depois: 1 linha de codigo, historico completo, instantaneo

3. Demo: GIF/video do dashboard em acao

4. Planos: Free / Pro / Enterprise
   - Tabela comparativa
   - CTA em cada plano

5. Depoimentos: (adicionar conforme coletar)

6. FAQ: perguntas comuns

7. Footer: links, GitHub, contato
```

**Dia 4: SEO basico**

1. Titulo: "BacenData - API de dados do Banco Central do Brasil"
2. Meta description com palavras-chave
3. Open Graph tags para compartilhamento
4. Google Analytics (GA4) — criar conta e instalar
5. Google Search Console — verificar dominio

**Dia 5: Formulario de cadastro**

1. Formulario simples: nome, email, empresa (opcional)
2. Salvar em Google Sheets ou Airtable (gratis)
3. Email de boas-vindas automatico (Mailchimp free tier)
4. Comecar a construir lista de emails

**Entregavel**: Landing page no ar com coleta de emails.

---

#### Semana 5: Dominio e infraestrutura

**Dia 1: Registrar dominio**

1. Acessar **Registro.br** (https://registro.br)
2. Registrar `bacendata.com.br` (R$40/ano)
3. Alternativa: `bacendata.dev` no Google Domains (~R$60/ano)
4. Configurar DNS apontando para a landing page

**Dia 2: Email profissional**

1. Criar `contato@bacendata.com.br`
2. Opcoes gratuitas: Zoho Mail free (5 usuarios) ou Gmail via Google Workspace ($6/mes)
3. Configurar SPF, DKIM e DMARC no DNS

**Dia 3: Escolher hospedagem da API**

| Plataforma | Free tier | Pro | Recomendacao |
|------------|-----------|-----|-------------|
| Railway | 500h/mes | $5/mes | Melhor DX |
| Render | 750h/mes | $7/mes | Mais estavel |
| Fly.io | 3 VMs | $0.57/mes | Mais controle |

**Recomendacao**: **Railway** para comecar (free tier generoso, deploy via GitHub).

**Dia 4-5: Deploy da API em producao**

1. Criar conta no Railway (https://railway.app)
2. Conectar repositorio GitHub
3. Configurar variaveis de ambiente (BACENDATA_API_KEYS, etc)
4. Deploy automatico: push na `main` = deploy
5. Configurar dominio customizado: `api.bacendata.com.br`
6. Testar todos os endpoints em producao
7. Configurar HTTPS (automatico no Railway)

**Entregavel**: API rodando em `https://api.bacendata.com.br`

---

#### Semana 6: Monitoramento e observabilidade

**Dia 1-2: Logging e erros**

1. Criar conta no **Sentry** (https://sentry.io) — free para 5K eventos/mes
2. Instalar SDK: `pip install sentry-sdk[fastapi]`
3. Configurar no `create_app()`:
   ```python
   import sentry_sdk
   sentry_sdk.init(dsn="...", traces_sample_rate=0.1)
   ```
4. Testar captura de erros

**Dia 3: Uptime monitoring**

1. Criar conta no **UptimeRobot** (https://uptimerobot.com) — gratis ate 50 monitores
2. Configurar monitor HTTP para `https://api.bacendata.com.br/health`
3. Alertas por email quando cair
4. Adicionar badge de status na landing page

**Dia 4-5: Metricas basicas**

1. Adicionar logging estruturado nas rotas (tempo de resposta, serie consultada)
2. Dashboard simples no Railway (ja tem metricas)
3. Criar planilha de acompanhamento:
   - Req/dia, usuarios unicos, series mais consultadas
   - Erros/dia, uptime %

**Entregavel**: Monitoramento ativo com alertas.

---

#### Semana 7: Stripe e pagamentos

**Objetivo**: Sistema de pagamentos funcionando.

**Dia 1: Criar conta Stripe**

1. Acessar https://dashboard.stripe.com/register
2. Preencher dados pessoais/empresa
3. **Importante**: para receber pagamentos no Brasil, voce precisa de CNPJ
4. Opcoes sem CNPJ: MEI (abrir em 15 min no gov.br) ou usar plataforma intermediaria

**Dia 2: Abrir MEI (se necessario)**

1. Acessar https://www.gov.br/empresas-e-negocios/pt-br/empreendedor
2. Atividade: "Desenvolvimento de programas de computador sob encomenda" (CNAE 6201-5/01)
3. Ou: "Portais, provedores de conteudo" (CNAE 6319-4/00)
4. Custo: R$0 para abrir, ~R$70/mes de DAS
5. Faturamento limite: R$81.000/ano (~R$6.750/mes)
6. Receber CNPJ na hora

**Dia 3: Configurar produtos no Stripe**

1. Criar produto "BacenData Pro" — R$79/mes (recorrente)
2. Criar produto "BacenData Enterprise" — R$299/mes (recorrente)
3. Criar Checkout Sessions para cada plano
4. Configurar webhook do Stripe para receber eventos (pagamento confirmado, cancelamento)

**Dia 4: Pagina de checkout**

1. Usar Stripe Checkout (hosted) — mais simples e seguro
2. Fluxo: Usuario clica "Assinar Pro" na landing page -> Stripe Checkout -> Sucesso -> Recebe API key por email
3. Configurar pagina de sucesso e cancelamento

**Dia 5: Testar fluxo completo**

1. Usar modo teste do Stripe (cartao 4242 4242 4242 4242)
2. Testar: cadastro -> pagamento -> recebe API key -> usa API
3. Testar: cancelamento -> API key desativada
4. Documentar o fluxo

**Entregavel**: Checkout funcionando com Stripe (modo teste).

---

#### Semana 8: Painel do usuario

**Objetivo**: Area logada onde o usuario gerencia assinatura e API keys.

**Dia 1-2: Autenticacao**

Opcoes (do mais simples ao mais completo):

| Opcao | Custo | Complexidade |
|-------|-------|-------------|
| Clerk.com | Gratis ate 10K MAU | Muito simples |
| Supabase Auth | Gratis ate 50K MAU | Simples |
| Auth proprio (JWT) | Gratis | Mais trabalho |

**Recomendacao**: **Clerk** para MVP (login com Google/GitHub, painel pronto, webhook para Stripe).

**Dia 3: Painel basico**

1. Dashboard do usuario mostrando:
   - Plano atual (Free/Pro/Enterprise)
   - Uso de requisicoes (X de Y req/dia)
   - API keys ativas
   - Botao "Gerar nova API key"
   - Botao "Upgrade" ou "Cancelar"

**Dia 4: Geracao de API keys**

1. Gerar UUID como API key no cadastro
2. Associar key ao plano do usuario
3. Armazenar hash da key (nunca texto plano)
4. Endpoint de validacao: checar key no banco antes de cada request

**Dia 5: Integrar Stripe com painel**

1. Webhook do Stripe atualiza plano no banco
2. Pagamento confirmado -> ativa plano Pro/Enterprise
3. Cancelamento -> rebaixa para Free
4. Falha no pagamento -> notifica usuario, grace period de 3 dias

**Entregavel**: Painel do usuario com gerenciamento de API keys.

---

#### Semana 9: Banco de dados PostgreSQL

**Objetivo**: Migrar de SQLite/in-memory para PostgreSQL em producao.

**Dia 1-2: Setup do banco**

1. Railway oferece PostgreSQL managed (free tier: 1GB)
2. Ou usar Supabase PostgreSQL (free: 500MB)
3. Criar tabelas:

```sql
-- Usuarios
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    nome TEXT,
    plano TEXT DEFAULT 'free',
    stripe_customer_id TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES usuarios(id),
    chave_hash TEXT NOT NULL,
    plano TEXT DEFAULT 'free',
    ativa BOOLEAN DEFAULT true,
    criada_em TIMESTAMP DEFAULT NOW()
);

-- Uso (para metricas)
CREATE TABLE uso_diario (
    id SERIAL PRIMARY KEY,
    api_key_id UUID REFERENCES api_keys(id),
    data DATE DEFAULT CURRENT_DATE,
    requisicoes INTEGER DEFAULT 0,
    UNIQUE(api_key_id, data)
);
```

**Dia 3-4: Migrar rate limiting para Redis/PostgreSQL**

1. Rate limiting atual e em memoria (perde ao reiniciar)
2. Opcao A: Redis (Railway add-on, free tier)
3. Opcao B: Tabela `uso_diario` no PostgreSQL (mais simples)
4. Validar API key no banco a cada requisicao (com cache de 60s)

**Dia 5: Cache de series no PostgreSQL**

1. Tabela para cache servidor (beneficio do plano Pro):

```sql
CREATE TABLE cache_series (
    id SERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL,
    data_inicio TEXT,
    data_fim TEXT,
    dados JSONB NOT NULL,
    atualizado_em TIMESTAMP DEFAULT NOW(),
    ttl_segundos INTEGER
);
```

2. Background job para atualizar as 14 series prioritarias

**Entregavel**: Banco de dados em producao com API keys persistidas.

---

#### Semana 10: Webhooks e alertas (feature Pro)

**Objetivo**: Notificar usuarios quando series atualizam.

**Dia 1-2: Sistema de webhooks**

1. Tabela de webhooks:

```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES usuarios(id),
    url TEXT NOT NULL,
    series INTEGER[] NOT NULL,
    ativo BOOLEAN DEFAULT true
);
```

2. Endpoint para cadastrar webhook: `POST /api/v1/webhooks`
3. Job que verifica atualizacoes a cada 1h (series diarias) ou 1x/dia (mensais)
4. Envia POST para a URL do usuario com dados atualizados

**Dia 3-4: Alertas por email**

1. Integrar com servico de email (SendGrid free: 100 emails/dia, ou Amazon SES)
2. Email quando serie atualiza: "IPCA de janeiro foi 0.42%"
3. Resumo semanal: "Semana no BACEN: Selic, IPCA, Dolar"

**Dia 5: Testar e documentar**

1. Testar webhook com https://webhook.site
2. Documentar na API.md
3. Adicionar como feature do plano Pro na landing page

**Entregavel**: Sistema de webhooks e alertas por email.

---

#### Semana 11: Marketing de conteudo

**Objetivo**: Gerar trafego organico para a landing page.

**Dia 1: LinkedIn (seu canal principal)**

1. Post de lancamento: "Criei uma API gratis para dados do BACEN"
   - Contar o problema (limitacao de 10 anos)
   - Mostrar a solucao (2 linhas de codigo)
   - CTA: link para PyPI/GitHub
   - Tags: #python #fintech #bacen #opendata

2. Agendar 2 posts/semana por 4 semanas:
   - "Como buscar 30 anos de Selic em Python com 1 linha"
   - "BACEN limitou a API em 2025. Criamos uma solucao."
   - "Dashboard gratis para acompanhar indicadores do BACEN"
   - "Por que criar uma API wrapper e a melhor forma de validar um SaaS"
   - "De projeto paralelo a primeiro cliente em 14 semanas"

**Dia 2: Twitter/X e comunidades**

1. Post no Twitter com demo em GIF
2. Compartilhar no:
   - r/brdev (Reddit)
   - TabNews
   - Dev.to (artigo em ingles)
   - Grupo "Python Brasil" no Telegram
   - Grupos de economia no WhatsApp/Telegram

**Dia 3: GitHub e PyPI**

1. Garantir README.md atraente com badges
2. Adicionar link para landing page no PyPI
3. Adicionar topics no GitHub: `bacen`, `brazil`, `finance`, `api`, `python`
4. Responder issues rapidamente (gera confianca)

**Dia 4: Artigo tecnico**

1. Escrever post no blog/Medium:
   "Como acessar dados do Banco Central em Python (guia completo 2025)"
   - Tutorial passo a passo com codigo
   - SEO: "api bacen python", "dados banco central"
   - CTA: link para PyPI e landing page

**Dia 5: Parcerias**

1. Contactar influenciadores de financas/python:
   - Canais YouTube de Python para financas
   - Newsletters de fintech (e.g., Finsiders, Startups.com.br)
   - Professores de economia computacional em universidades
2. Oferecer acesso Pro gratuito em troca de review/mencao

**Entregavel**: Primeiros posts publicados, trafego comecando.

---

#### Semana 12: Lancamento oficial

**Dia 1: Preparacao**

1. Revisar landing page (textos, links, checkout)
2. Testar fluxo completo: cadastro -> pagamento -> API key -> usar API
3. Preparar email de lancamento para a lista
4. Preparar post "grande" do LinkedIn

**Dia 2: Lancamento no Product Hunt**

1. Criar conta no Product Hunt (https://www.producthunt.com)
2. Preparar assets: logo, screenshot, tagline
3. Agendar lancamento para terca ou quarta (melhores dias)
4. Pedir para amigos/conhecidos upvotarem no dia

**Dia 3: Lancamento**

1. Publicar no Product Hunt
2. Publicar post principal no LinkedIn
3. Enviar email para lista de cadastros
4. Postar em todas as comunidades (Reddit, Twitter, TabNews)
5. Responder todos os comentarios no dia

**Dia 4-5: Acompanhamento**

1. Monitorar metricas: visitas, cadastros, downloads PyPI
2. Responder feedback e perguntas
3. Corrigir bugs reportados imediatamente
4. Agradecer publicamente quem compartilhou

**Entregavel**: Lancamento oficial concluido.

---

#### Semana 13: Vendas ativas

**Dia 1-2: Outbound para fintechs**

1. Listar 50 fintechs brasileiras que usam dados BACEN:
   - Creditas, Nubank, Inter, C6, PicPay (dados de credito)
   - XP, BTG, Modal, Warren (dados de juros/cambio)
   - Serasa, Quod, Boa Vista (inadimplencia)
2. Encontrar o CTO/lead dev no LinkedIn
3. Mensagem personalizada:
   > "Oi [Nome], vi que a [Fintech] trabalha com dados de credito.
   > Criamos uma API que simplifica o acesso ao BACEN SGS.
   > Oferecemos 30 dias gratis do plano Pro. Quer testar?"

**Dia 3: Trial gratuito**

1. Criar sistema de trial: 30 dias Pro gratis
2. Gerar API key Pro temporaria
3. Email de onboarding com docs e exemplos
4. Lembrete no dia 25: "Seu trial expira em 5 dias"

**Dia 4-5: Outbound para consultorias**

1. Listar consultorias financeiras (buscar no LinkedIn "consultoria financeira economia")
2. Mesma abordagem: mensagem personalizada + trial
3. Foco no dashboard: "Seus analistas nao precisam mais baixar CSV manualmente"

**Entregavel**: 20-50 trials ativos.

---

#### Semana 14: Primeiro faturamento

**Dia 1-2: Converter trials**

1. Acompanhar uso dos trials (quem esta usando de verdade?)
2. Email personalizado para heavy users:
   > "Vi que voce consultou 500+ series essa semana.
   > O plano Pro garante 10.000 req/dia e cache servidor.
   > Use o cupom EARLY20 para 20% off no primeiro mes."

**Dia 3: Ativar Stripe em modo producao**

1. Completar verificacao do Stripe (CNPJ, conta bancaria)
2. Mudar de modo teste para producao
3. Ativar checkout real
4. Primeiro pagamento!

**Dia 4-5: Rotina pos-lancamento**

1. Publicar metricas da semana 1 (transparencia gera confianca)
2. Atualizar roadmap publico
3. Planejar proximas features baseado em feedback
4. Comecar ciclo de conteudo semanal (1 post LinkedIn + 1 artigo/mes)

**Entregavel**: Primeiro cliente pagante!

---

## 7. Infraestrutura e Custos

### Custos mensais estimados (inicio)

| Item | Custo/mes | Notas |
|------|----------|-------|
| Railway (API + PostgreSQL) | R$0-25 | Free tier cobre inicio |
| Dominio (.com.br) | R$3 | R$40/ano |
| Streamlit Cloud (dashboard) | R$0 | Free para projetos publicos |
| Stripe | 3.99% + R$0.39/transacao | So cobra quando vende |
| Sentry (erros) | R$0 | Free tier: 5K eventos/mes |
| UptimeRobot | R$0 | Free: 50 monitores |
| MEI (DAS) | R$70 | Obrigatorio para emitir nota |
| Email (Zoho) | R$0 | Free: 5 usuarios |
| Carrd (landing page) | R$8 | $19/ano |
| **TOTAL** | **~R$106/mes** | Antes de qualquer receita |

### Break-even

- Custo fixo: ~R$106/mes
- Preco Pro: R$79/mes (liquido apos Stripe: ~R$72)
- **Break-even: 2 clientes Pro**

### Custos quando escalar (10+ clientes)

| Item | Custo/mes | Notas |
|------|----------|-------|
| Railway (API + DB + Redis) | R$100 | Starter plan |
| Dominio | R$3 | |
| Stripe (10 clientes Pro) | R$43 | 3.99% de R$790 + taxas |
| Sentry | R$0-130 | Free ou Team |
| SendGrid (emails) | R$0 | Free: 100/dia |
| MEI | R$70 | |
| **TOTAL** | **~R$350/mes** | |
| **RECEITA** | **~R$790/mes** | 10 clientes Pro |
| **LUCRO** | **~R$440/mes** | |

---

## 8. Marketing e Aquisicao

### Canais por prioridade

| Canal | Custo | Esforco | Resultado esperado |
|-------|-------|---------|-------------------|
| 1. PyPI/GitHub (organico) | R$0 | Ja feito | 50-100 instalacoes/mes |
| 2. LinkedIn (posts) | R$0 | 2h/semana | 500-2K views/post |
| 3. Comunidades (Reddit, TabNews) | R$0 | 1h/semana | 100-500 cliques |
| 4. Artigos tecnicos (Medium, Dev.to) | R$0 | 4h/artigo | SEO de longo prazo |
| 5. Product Hunt (lancamento) | R$0 | 1 dia | 200-1K visitas no dia |
| 6. Outbound (LinkedIn msgs) | R$0 | 2h/semana | 5-10 trials/semana |
| 7. Google Ads (futuro) | R$500/mes | 1h/semana | CPC ~R$2-5 |

### Metricas de aquisicao esperadas

| Mes | Instalacoes PyPI | Visitas LP | Cadastros | Trials | Clientes Pro |
|-----|-----------------|-----------|-----------|--------|-------------|
| 1 | 100 | 500 | 50 | 10 | 1-2 |
| 3 | 300 | 1.500 | 150 | 30 | 5-8 |
| 6 | 600 | 3.000 | 300 | 50 | 15-20 |
| 12 | 1.500 | 8.000 | 800 | 100 | 30-50 |

---

## 9. Metricas e KPIs

### KPIs semanais (acompanhar toda segunda-feira)

| Metrica | Meta mes 1 | Meta mes 3 | Meta mes 6 |
|---------|-----------|-----------|-----------|
| Downloads PyPI (acumulado) | 100 | 500 | 2.000 |
| GitHub stars | 20 | 100 | 500 |
| Visitas landing page/mes | 500 | 1.500 | 5.000 |
| Cadastros email | 50 | 200 | 500 |
| Usuarios Free ativos | 20 | 80 | 200 |
| Clientes Pro | 1 | 5 | 15 |
| Clientes Enterprise | 0 | 0 | 1-2 |
| MRR (receita recorrente) | R$79 | R$395 | R$1.500+ |
| Churn mensal | <10% | <10% | <8% |
| Uptime da API | 99% | 99.5% | 99.5% |

### Como acompanhar

1. **Planilha semanal** no Google Sheets com historico
2. **Google Analytics** para landing page
3. **Railway dashboard** para metricas da API
4. **Stripe Dashboard** para MRR e churn
5. **PyPI stats**: https://pypistats.org/packages/bacendata

---

## 10. Aspectos Legais

### MEI — Obrigatorio para faturar

1. **Abrir MEI** em https://www.gov.br/empresas-e-negocios/pt-br/empreendedor
2. **CNAE**: 6201-5/01 (Desenvolvimento de software sob encomenda)
3. **Custo**: R$70/mes (DAS mensal)
4. **Limite**: R$81.000/ano (~R$6.750/mes)
5. **Nota fiscal**: Emitir via portal da prefeitura (NFSe)
6. **Quando migrar**: Se ultrapassar R$6.750/mes, migrar para ME (Simples Nacional)

### Termos de uso (criar antes do lancamento)

1. **Termos de Servico**: Definir SLA, limites, uso aceitavel
2. **Politica de Privacidade**: LGPD compliant (email, dados de uso)
3. **Politica de Reembolso**: 7 dias conforme CDC
4. Usar template e adaptar (nao precisa de advogado no inicio)
5. Publicar na landing page

### Dados publicos do BACEN

- Dados da API SGS sao **publicos e gratuitos** (Lei de Acesso a Informacao)
- Voce pode comercializar o **acesso facilitado** (API, cache, dashboard)
- Voce NAO pode comercializar os dados como se fossem seus
- Sempre atribuir fonte: "Dados: Banco Central do Brasil — SGS"
- Nao ha problema legal em cobrar pelo servico de intermediacao

### Propriedade intelectual

- Codigo: seu, licenca MIT (bom para marketing, devs confiam)
- Marca "BacenData": registrar no INPI quando faturar (R$142 online)
  - https://www.gov.br/inpi/pt-br
  - Classe: 42 (servicos de tecnologia)

---

## 11. Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|-------------|---------|-----------|
| BACEN muda/bloqueia API SGS | Baixa | Alto | Cache agressivo, scraping como fallback, diversificar fontes |
| Concorrente grande (ex: Bloomberg) cria produto similar | Baixa | Medio | Foco no nicho BR, preco imbativel, comunidade |
| Poucos clientes pagantes | Media | Alto | Validar com trials antes de investir; pivotar para consultoria se necessario |
| Problema de disponibilidade | Media | Medio | Monitoramento, cache, multiplos workers |
| Faturamento ultrapassa limite MEI | Baixa (bom problema!) | Baixo | Migrar para ME no Simples Nacional |
| BACEN exige autorizacao para wrappers | Muito baixa | Alto | Dados publicos, Lei de Acesso a Informacao protege |

---

## 12. Projecao Financeira

### Cenario conservador (12 meses)

| Mes | Clientes Pro | Clientes Enterprise | MRR | Custos | Lucro |
|-----|-------------|--------------------|----|--------|-------|
| 1 | 1 | 0 | R$79 | R$106 | -R$27 |
| 2 | 2 | 0 | R$158 | R$106 | R$52 |
| 3 | 5 | 0 | R$395 | R$150 | R$245 |
| 4 | 7 | 0 | R$553 | R$150 | R$403 |
| 5 | 10 | 0 | R$790 | R$200 | R$590 |
| 6 | 12 | 1 | R$1.247 | R$250 | R$997 |
| 7 | 15 | 1 | R$1.484 | R$250 | R$1.234 |
| 8 | 18 | 1 | R$1.721 | R$300 | R$1.421 |
| 9 | 20 | 2 | R$2.178 | R$300 | R$1.878 |
| 10 | 23 | 2 | R$2.415 | R$350 | R$2.065 |
| 11 | 25 | 2 | R$2.573 | R$350 | R$2.223 |
| 12 | 30 | 3 | R$3.267 | R$400 | R$2.867 |

### Resumo anual (cenario conservador)

| Metrica | Valor |
|---------|-------|
| **Receita anual** | ~R$17.000 |
| **Custos anuais** | ~R$3.000 |
| **Lucro anual** | ~R$14.000 |
| **Clientes ao final do ano** | 33 pagantes |
| **MRR ao final do ano** | R$3.267 |

### Cenario otimista (12 meses)

| Metrica | Valor |
|---------|-------|
| **Clientes Pro** | 60 |
| **Clientes Enterprise** | 8 |
| **MRR** | R$7.132 |
| **Receita anual** | ~R$45.000 |
| **Lucro anual** | ~R$38.000 |

### Quando fica interessante?

| Marco | Quando (estimativa) |
|-------|-------------------|
| Break-even (custo zero) | Mes 2 (2 clientes Pro) |
| R$1.000/mes de lucro | Mes 6 (12 Pro + 1 Enterprise) |
| R$3.000/mes de lucro | Mes 12 (30 Pro + 3 Enterprise) |
| Limite MEI (R$6.750/mes) | Mes 18-24 |
| Renda equivalente ao emprego | 24-36 meses |

---

## Checklist Final: Proximos Passos Imediatos

### Esta semana (agora!)

- [ ] Decidir: comecar pelo dashboard (Fase 3) ou ir direto para monetizacao (Fase 4)?
- [ ] Abrir MEI (15 minutos no gov.br)
- [ ] Registrar dominio `bacendata.com.br` no Registro.br
- [ ] Criar conta no Railway para deploy
- [ ] Criar conta no Stripe

### Proximo mes

- [ ] Dashboard Streamlit publicado
- [ ] Landing page no ar com coleta de emails
- [ ] API em producao com dominio proprio
- [ ] Primeiro post no LinkedIn

### Em 3 meses

- [ ] Checkout Stripe funcionando
- [ ] 5 clientes Pro pagando
- [ ] 500 downloads no PyPI
- [ ] MRR > R$395

---

> **Lembrete**: Voce nao precisa fazer tudo de uma vez. O segredo e manter momentum: uma entrega pequena por semana e melhor que um lancamento perfeito que nunca acontece. Ship it!
