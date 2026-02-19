# CLAUDE.md — BacenData Platform

## Visão do Projeto

**BacenData** é uma plataforma SaaS que simplifica o acesso, consumo e visualização de dados públicos do Banco Central do Brasil. O produto resolve a dor de analistas, fintechs, economistas e desenvolvedores que precisam consumir dados do BACEN mas enfrentam APIs mal documentadas, limitações recentes de volume e ausência de ferramentas amigáveis.

### Contexto de Negócio

- **Fundador**: Felipe, 45 anos, senior data scientist e analista de risco de crédito no BNDES
- **Diferencial**: Profundo conhecimento da API SGS/BACEN, modelagem financeira e Python
- **Modelo de receita**: Freemium → Pro (R$49-99/mês) → Enterprise (R$299-499/mês)
- **Disponibilidade para o projeto**: 10-20 horas/semana (projeto paralelo ao emprego)

### Problema que Resolvemos

1. A API SGS do BACEN passou a limitar consultas a 10 anos e exigir filtros obrigatórios (março/2025)
2. O portal de dados abertos do BACEN tem UX ruim e não oferece dashboards prontos
3. Não existe uma API wrapper moderna, bem documentada e com cache inteligente
4. Analistas perdem horas fazendo download manual e tratamento de séries

### Mudança na API BACEN (Março 2025)

- Consultas JSON/CSV de séries diárias agora têm volume limitado
- Filtro de datas obrigatório (antes era opcional)
- Limite máximo de 10 anos por consulta
- Endpoint base mantido: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`
- Formatos: `?formato=json` ou `?formato=csv`
- Últimos N valores: `.../dados/ultimos/{N}?formato=json`

---

## Arquitetura

### Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Backend API | FastAPI (Python 3.11+) | Performance, async, tipagem, docs automáticas |
| Banco de Dados | PostgreSQL | Cache de séries, metadados, usuários |
| Cache | Redis (opcional no MVP) | Rate limiting, cache quente |
| Frontend MVP | Streamlit ou React | Streamlit para MVP rápido, React para v2 |
| Deploy | Railway / Render / Fly.io | Free tier para começar |
| CI/CD | GitHub Actions | Testes + deploy automático |
| Monitoramento | Sentry + logging estruturado | Erros e observabilidade |

### Estrutura do Repositório

```
bacendata/
├── CLAUDE.md                  # Este arquivo
├── README.md                  # Documentação pública
├── pyproject.toml             # Dependências e config do projeto
├── .env.example               # Variáveis de ambiente template
├── .github/
│   └── workflows/
│       ├── ci.yml             # Testes + lint
│       └── deploy.yml         # Deploy automático
├── src/
│   ├── bacendata/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Settings com pydantic-settings
│   │   │   └── database.py    # Conexão PostgreSQL (SQLAlchemy async)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py         # FastAPI app factory
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── series.py  # Endpoints de séries temporais
│   │   │   │   ├── health.py  # Health check
│   │   │   │   └── auth.py    # Autenticação (API keys)
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       └── rate_limit.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── bacen_client.py    # Client da API SGS com paginação automática
│   │   │   ├── cache_service.py   # Lógica de cache e atualização
│   │   │   └── series_catalog.py  # Catálogo de séries populares
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── series.py     # SQLAlchemy models
│   │   │   └── user.py       # Modelo de usuário/API key
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── series.py     # Pydantic schemas (request/response)
│   └── wrapper/
│       ├── __init__.py
│       └── bacen_sgs.py       # Wrapper Python standalone (pode ser pip install)
├── frontend/
│   └── app.py                 # Streamlit dashboard (MVP)
├── scripts/
│   ├── seed_catalog.py        # Popular catálogo de séries
│   ├── update_cache.py        # Cron job para atualizar cache
│   └── migrate.py             # Migrações de banco
├── tests/
│   ├── __init__.py
│   ├── test_bacen_client.py
│   ├── test_api.py
│   └── test_wrapper.py
└── docs/
    ├── API.md                 # Documentação da API REST
    ├── WRAPPER.md             # Docs do wrapper Python
    └── SERIES_CATALOG.md      # Lista de séries disponíveis
```

---

## Regras de Desenvolvimento

### Princípios

1. **MVP first**: Funcionalidade mínima que entrega valor. Não over-engineer.
2. **Wrapper primeiro**: O wrapper Python standalone é o primeiro deliverable — pode ser publicado no PyPI e gera tração.
3. **Testes sempre**: Mínimo de 80% cobertura nos módulos core.
4. **Type hints obrigatórios**: Código tipado em todo lugar.
5. **Docstrings em português**: Documentação voltada ao público brasileiro.
6. **Async by default**: FastAPI async para I/O bound (chamadas ao BACEN).

### Convenções de Código

- **Python**: PEP 8, black formatter, ruff linter
- **Commits**: Conventional commits em português (`feat:`, `fix:`, `docs:`, `refactor:`)
- **Branches**: `main` (produção), `develop` (dev), `feat/xxx` (features)
- **Variáveis de ambiente**: Nunca hardcode. Usar `.env` + pydantic-settings

### Padrões de Tratamento de Dados

- Datas sempre no formato ISO 8601 internamente
- API aceita formato brasileiro (dd/MM/yyyy) e converte internamente
- Valores numéricos como `float` (nunca string)
- Timezone: UTC para armazenamento, conversão para BRT na apresentação
- Séries retornadas sempre como JSON com campos: `data`, `valor`, `serie_codigo`, `serie_nome`

---

## Séries Prioritárias (MVP)

Estas são as séries mais demandadas e devem estar no cache desde o dia 1:

| Código | Nome | Periodicidade |
|--------|------|---------------|
| 11 | Taxa Selic (diária) | Diária |
| 12 | Taxa Selic acumulada no mês | Mensal |
| 433 | IPCA (variação mensal) | Mensal |
| 4390 | Taxa Selic acumulada no mês anualizada | Mensal |
| 1 | Taxa de câmbio - Dólar (compra) | Diária |
| 21619 | Taxa de câmbio - Euro (compra) - PTAX | Diária |
| 4189 | Taxa média de juros - Pessoa Física | Mensal |
| 25434 | Taxa média de juros - Crédito Livre Total | Mensal |
| 20542 | Saldo carteira crédito recursos livres - Total | Mensal |
| 21112 | Inadimplência crédito - PF | Mensal |
| 21082 | Inadimplência crédito - PJ | Mensal |
| 7326 | Reservas internacionais | Diária |
| 27574 | Expectativa IPCA 12 meses (Focus) | Semanal |
| 27575 | Expectativa Selic (Focus) | Semanal |

---

## Roadmap

### Fase 1 — Wrapper Python (Semanas 1-3)
- [ ] Módulo `bacen_sgs.py` com paginação automática para >10 anos
- [ ] Suporte a múltiplas séries em uma chamada
- [ ] Retorno como pandas DataFrame
- [ ] Tratamento robusto de erros (retry, timeout, rate limit)
- [ ] Testes unitários e de integração
- [ ] Publicar no PyPI como `bacendata`
- [ ] README.md com exemplos claros

### Fase 2 — API REST (Semanas 3-6)
- [ ] FastAPI com endpoints: `/series/{codigo}`, `/series/search`, `/series/bulk`
- [ ] Cache em PostgreSQL com TTL por periodicidade da série
- [ ] Autenticação por API key
- [ ] Rate limiting (free: 100 req/dia, pro: 10.000 req/dia)
- [ ] Documentação OpenAPI automática
- [ ] Deploy inicial (Railway/Render)

### Fase 3 — Dashboard (Semanas 6-10)
- [ ] Streamlit dashboard com séries pré-configuradas
- [ ] Gráficos interativos (Plotly)
- [ ] Comparação de séries lado a lado
- [ ] Download CSV/Excel
- [ ] Filtros de período amigáveis

### Fase 4 — Monetização (Semanas 10-14)
- [ ] Landing page (React ou Next.js)
- [ ] Sistema de planos (Stripe)
- [ ] Painel do usuário (gerenciar API keys)
- [ ] Alertas de atualização de séries (email/webhook)
- [ ] Documentação completa para desenvolvedores

---

## Decisões Técnicas Importantes

### Por que FastAPI e não Flask/Django?
- Async nativo (essencial para chamadas à API BACEN)
- Documentação OpenAPI automática (reduz trabalho manual)
- Pydantic integrado (validação de dados "de graça")
- Performance superior para I/O bound

### Por que PostgreSQL e não SQLite?
- Concorrência real (múltiplos workers)
- Suporte nativo a JSON (séries temporais)
- Escalável para produção sem migração
- Todos os PaaS oferecem PostgreSQL managed

### Por que wrapper separado?
- Pode ser usado standalone (pip install bacendata)
- Marketing: open source no PyPI gera tráfego e credibilidade
- Developers experimentam o wrapper → convertem para API paga
- Funnel: PyPI → GitHub → Landing page → Assinatura

### Estratégia de Cache
- Séries diárias: cache de 1 hora durante horário comercial, 24h fora
- Séries mensais: cache de 24 horas
- Séries semanais (Focus): cache de 6 horas
- Background job atualiza séries prioritárias automaticamente
- Cache miss: busca na API BACEN em tempo real + armazena

---

## Comandos Úteis

```bash
# Setup do ambiente
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Rodar testes
pytest tests/ -v --cov=src/bacendata

# Rodar API localmente
uvicorn src.bacendata.api.app:create_app --factory --reload --port 8000

# Rodar dashboard
streamlit run frontend/app.py

# Lint e formatação
ruff check src/ tests/
black src/ tests/

# Seed do catálogo de séries
python scripts/seed_catalog.py
```

---

## Notas para o Claude Code

- Sempre pergunte antes de criar arquivos fora da estrutura definida acima
- Priorize código funcional e testável sobre perfeição
- Use httpx (async) para chamadas HTTP, não requests
- Pandas é dependência do wrapper, não do core da API
- Erros da API BACEN devem ser logados e retornados como HTTP 502 com mensagem clara
- Nunca faça mais de 5 requisições simultâneas à API BACEN (seja gentil com o servidor público)
- O público-alvo é brasileiro: docstrings, logs e mensagens de erro em português
