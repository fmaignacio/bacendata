# BacenData — Especificação Completa do Projeto

## 1. Resumo Executivo

**BacenData** é uma plataforma que democratiza o acesso a dados econômicos do Banco Central do Brasil, oferecendo um wrapper Python open-source, uma API REST com cache inteligente e um dashboard interativo para visualização de séries temporais.

**Público-alvo primário:**
- Analistas financeiros e economistas que consomem dados do BACEN regularmente
- Fintechs que precisam de dados macroeconômicos para seus produtos
- Desenvolvedores Python que trabalham com dados econômicos brasileiros
- Pesquisadores acadêmicos e jornalistas de dados

**Proposta de valor:** "Dados do BACEN em 1 linha de código, sem limitações."

---

## 2. Análise de Mercado

### 2.1 Problema

Em março de 2025, o Banco Central limitou as consultas à API SGS:
- Volume de dados retornados agora é limitado para séries diárias
- Filtro de datas tornou-se obrigatório
- Consultas por período limitadas a 10 anos

Isso quebrou scripts de milhares de analistas e desenvolvedores. Bibliotecas como `python-bcb` (Wilson Freitas) funcionam mas não tratam essas limitações automaticamente.

### 2.2 Concorrência

| Solução | Tipo | Limitações |
|---------|------|------------|
| API SGS direta | API pública | Sem cache, limitações novas, sem docs amigáveis |
| python-bcb | Lib Python | Não trata limites de 10 anos, sem API REST |
| IPEADATA | Portal + API | Subconjunto dos dados, interface datada |
| Bloomberg/Refinitiv | SaaS enterprise | USD 20k+/ano, overkill para maioria |

### 2.3 Oportunidade

Não existe hoje uma solução que combine:
1. Wrapper Python moderno com paginação automática
2. API REST com cache e documentação
3. Dashboard visual gratuito
4. Preço acessível (R$ 49-499/mês)

---

## 3. Funcionalidades por Fase

### Fase 1: Wrapper Python (MVP — 3 semanas)

**Objetivo:** Publicar no PyPI um pacote que qualquer dev instale com `pip install bacendata`

```python
# Uso desejado:
from bacendata import sgs

# Buscar uma série
selic = sgs.get(11, start="2000-01-01")  # Pagina automaticamente se >10 anos

# Buscar múltiplas séries
df = sgs.get({
    "Selic": 11,
    "IPCA": 433,
    "Dólar": 1
}, start="2010-01-01", end="2024-12-31")

# Últimos N valores
ipca_recente = sgs.get(433, last=12)

# Buscar metadados de uma série
info = sgs.metadata(433)
```

**Features:**
- Paginação automática transparente (divide consultas >10 anos em chunks)
- Retorno como pandas DataFrame
- Suporte a múltiplas séries simultâneas (async sob o capô)
- Retry automático com backoff exponencial
- Rate limiting inteligente (máximo 5 req/s)
- Cache local opcional (SQLite)
- Metadados de séries (nome, periodicidade, fonte)
- Catálogo de séries populares integrado

### Fase 2: API REST (Semanas 3-6)

**Endpoints:**

```
GET  /api/v1/series/{codigo}
     ?start=2020-01-01
     &end=2024-12-31
     &format=json|csv
     → Retorna série temporal com cache

GET  /api/v1/series/{codigo}/latest
     ?n=10
     → Últimos N valores

GET  /api/v1/series/{codigo}/metadata
     → Metadados da série

GET  /api/v1/series/search
     ?q=selic
     → Busca no catálogo de séries

POST /api/v1/series/bulk
     body: {"series": [11, 433, 1], "start": "2020-01-01"}
     → Múltiplas séries em uma chamada

GET  /api/v1/health
     → Status da API e última atualização do cache
```

**Autenticação:**
- Free tier: sem chave, 100 req/dia por IP
- Pro: API key no header `X-API-Key`, 10.000 req/dia
- Enterprise: API key, 100.000 req/dia + suporte

### Fase 3: Dashboard (Semanas 6-10)

- Dashboard Streamlit público com séries pré-configuradas
- Seletor de séries com autocomplete
- Gráficos Plotly interativos (zoom, hover, download)
- Comparação lado a lado (até 4 séries)
- Tabela com dados brutos + download CSV/Excel
- Indicadores macro em cards (Selic atual, IPCA acumulado, Dólar)

### Fase 4: Monetização (Semanas 10-14)

- Landing page profissional
- Checkout via Stripe
- Painel do usuário (gerar/revogar API keys)
- Alertas de atualização (webhook + email)
- Documentação interativa (Swagger + exemplos em Python/JS/R)

---

## 4. Modelo de Negócio

### 4.1 Planos

| Plano | Preço | Limites | Público |
|-------|-------|---------|---------|
| Free | R$ 0 | 100 req/dia, 5 séries por bulk | Estudantes, curiosos |
| Pro | R$ 79/mês | 10.000 req/dia, 50 séries por bulk, cache prioritário | Analistas, pequenas fintechs |
| Enterprise | R$ 399/mês | 100.000 req/dia, séries ilimitadas, SLA 99.5%, suporte | Fintechs, bancos médios |

### 4.2 Projeção Conservadora (12 meses)

| Mês | Free users | Pro | Enterprise | MRR |
|-----|-----------|-----|-----------|-----|
| 3 | 100 | 2 | 0 | R$ 158 |
| 6 | 500 | 10 | 1 | R$ 1.189 |
| 9 | 1.500 | 25 | 3 | R$ 3.172 |
| 12 | 3.000 | 50 | 5 | R$ 5.945 |

**Break-even estimado:** Mês 8-10 (custos de infra ~R$ 200-500/mês)

### 4.3 Canais de Aquisição

1. **PyPI + GitHub** (orgânico): Devs encontram o wrapper, usam de graça, convertem para Pro
2. **LinkedIn** (conteúdo): Posts sobre economia + dados, direcionando para a plataforma
3. **SEO**: Dashboard público indexado com séries populares ("Selic histórica", "IPCA acumulado")
4. **Comunidades**: Data Hackers, Python Brasil, grupos de economia no Telegram
5. **Indicação**: Programa de referral simples (1 mês grátis por indicação convertida)

---

## 5. Especificação Técnica do Wrapper (Fase 1 — Detalhe)

### 5.1 Módulo `bacen_sgs.py`

```python
"""
bacendata.wrapper.bacen_sgs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cliente para a API SGS do Banco Central do Brasil.
Trata automaticamente as limitações de consulta impostas em março/2025.
"""

import httpx
import pandas as pd
from datetime import date, datetime
from typing import Union, Optional

# Constantes
BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
MAX_YEARS_PER_REQUEST = 10
MAX_CONCURRENT_REQUESTS = 5
DEFAULT_TIMEOUT = 30  # segundos
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 5]  # segundos entre retries
```

### 5.2 Lógica de Paginação

Quando `start` e `end` formam um intervalo > 10 anos:
1. Dividir em chunks de 10 anos
2. Fazer chamadas async (máximo 5 simultâneas)
3. Concatenar resultados
4. Remover duplicatas nas bordas dos chunks
5. Ordenar por data

### 5.3 Tratamento de Erros

| Erro | Ação |
|------|------|
| HTTP 429 (rate limit) | Retry com backoff exponencial |
| HTTP 500/502/503 | Retry até 3x |
| HTTP 400 (filtro inválido) | Raise exceção clara em português |
| Timeout | Retry com timeout aumentado |
| Série inexistente | Raise `SerieNaoEncontrada` |
| Dados vazios | Retornar DataFrame vazio com log warning |

### 5.4 Dependências do Wrapper

```toml
[project]
name = "bacendata"
version = "0.1.0"
description = "Acesso simplificado aos dados do Banco Central do Brasil"
requires-python = ">=3.9"
dependencies = [
    "httpx>=0.25.0",
    "pandas>=1.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "black>=23.0",
    "respx>=0.20",  # Mock para httpx
]
cache = [
    "aiosqlite>=0.19",
]
```

---

## 6. Infraestrutura e Deploy

### 6.1 Ambiente de Desenvolvimento

```bash
# Pré-requisitos
Python 3.11+
PostgreSQL 15+ (para Fase 2+)
Node.js 18+ (para frontend React na Fase 4)

# Setup
git clone https://github.com/<seu-usuario>/bacendata.git
cd bacendata
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 6.2 Deploy (Fase 2+)

**Opção recomendada: Railway**
- PostgreSQL managed incluso no plano hobby
- Deploy automático via GitHub
- SSL gratuito
- Custo: ~$5-20/mês inicialmente

**Alternativa: Render**
- Free tier com PostgreSQL (limitado)
- Deploy via GitHub
- Bom para MVP

### 6.3 Variáveis de Ambiente

```env
# .env.example
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/bacendata
REDIS_URL=redis://localhost:6379  # Opcional no MVP
API_SECRET_KEY=sua-chave-secreta
BACEN_MAX_CONCURRENT=5
BACEN_TIMEOUT=30
STRIPE_SECRET_KEY=sk_...  # Fase 4
SENTRY_DSN=https://...  # Opcional
```

---

## 7. Métricas de Sucesso

### Fase 1 (Wrapper)
- ✅ 50+ stars no GitHub em 30 dias
- ✅ 100+ downloads/semana no PyPI
- ✅ 0 bugs críticos reportados

### Fase 2 (API)
- ✅ 99.5% uptime
- ✅ < 200ms tempo de resposta (cache hit)
- ✅ 50+ usuários registrados

### Fase 3 (Dashboard)
- ✅ 500+ visitas/mês
- ✅ 3+ minutos tempo médio na página
- ✅ Primeiras conversões free → pro

### Fase 4 (Monetização)
- ✅ R$ 1.000+ MRR
- ✅ 5+ clientes pagantes
- ✅ Churn < 10%/mês

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| BACEN bloquear scraping/API | Baixa | Alto | Dados são públicos por lei; manter rate limit baixo |
| python-bcb adicionar mesmas features | Média | Médio | Diferenciar pela API REST + dashboard + suporte |
| Poucos usuários pagantes | Média | Alto | Focar em conteúdo/SEO; validar pricing com early adopters |
| Custo de infra escalar | Baixa | Baixo | Cache agressivo; escalar conforme receita |
| Falta de tempo do fundador | Alta | Alto | MVP mínimo; automatizar o máximo possível |

---

## 9. Ações Imediatas (Esta Semana)

1. [ ] Criar repositório GitHub `bacendata`
2. [ ] Copiar CLAUDE.md para a raiz
3. [ ] Implementar `bacen_sgs.py` com paginação automática
4. [ ] Escrever testes para o wrapper
5. [ ] Criar README.md atrativo com exemplos
6. [ ] Configurar CI (GitHub Actions)
7. [ ] Publicar v0.1.0 no PyPI

---

*Documento gerado em 07/02/2026. Atualizar conforme decisões evoluem.*
