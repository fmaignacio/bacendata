# Posts Reddit

## r/brdev — Título: "Criei um wrapper Python para a API do Banco Central (SGS) com paginação automática"

Fala pessoal,

Criei o **BacenData**, um wrapper Python open source para a API SGS do Banco Central.

**O problema:** Em março de 2025, o BACEN limitou consultas a 10 anos por requisição. Se você precisa de séries históricas longas (Dólar desde 1984, Selic desde 1986), precisa fazer várias chamadas e combinar manualmente.

**A solução:**

```python
pip install bacendata

from bacendata import sgs

# Série completa do Dólar (paginação automática)
dolar = sgs.get("dolar", start="1984-01-01")

# Múltiplas séries de uma vez
df = sgs.get({"Selic": 11, "IPCA": 433}, start="2010-01-01")

# Últimos 12 valores
ipca = sgs.get("ipca", last=12)
```

**Features:**
- Paginação automática (divide em chunks de 10 anos, requisições paralelas)
- 14 séries pré-configuradas com aliases (selic, ipca, dolar, euro, etc.)
- Cache SQLite local com TTL
- Retry automático com backoff exponencial
- Retorna pandas DataFrame
- API REST com FastAPI
- Dashboard interativo com Streamlit

**Stack:** Python 3.10+, httpx (async), asyncio, FastAPI, Streamlit, Plotly

**Links:**
- GitHub: https://github.com/fmaignacio/bacendata
- PyPI: https://pypi.org/project/bacendata/
- Dashboard: https://bacendata.streamlit.app
- Site: https://bacendata.com

Aceito feedback e PRs. O que acham?

---

## r/investimentos — Título: "Dashboard gratuito com indicadores do Banco Central (Selic, IPCA, câmbio, crédito)"

Criei um dashboard gratuito e open source para visualizar indicadores econômicos do Banco Central do Brasil.

**O que tem:**
- Selic (diária, mensal, anualizada)
- IPCA (inflação mensal)
- Dólar e Euro (PTAX diária)
- Juros de crédito (PF e PJ)
- Inadimplência (PF e PJ)
- Reservas internacionais
- Expectativas Focus (IPCA e Selic)

**Features:**
- Gráficos interativos (zoom, hover com valores)
- Comparação lado a lado de até 3 séries
- Média móvel configurável
- Download CSV/Excel
- Correlação entre séries

**Acesse:** https://bacendata.streamlit.app

Também tem um wrapper Python para quem quer usar programaticamente: `pip install bacendata`

Feedback é bem-vindo!

---

## r/Python — Título: "bacendata: Python wrapper for Brazil's Central Bank API with automatic pagination"

I built **bacendata**, an open source Python wrapper for Brazil's Central Bank (BACEN) SGS API.

**The problem:** In March 2025, BACEN limited API queries to 10 years per request. If you need long historical series (e.g., USD/BRL exchange rate since 1984), you need multiple calls and manual concatenation.

**The solution:**

```python
from bacendata import sgs

# Automatic pagination for 40+ years of data
usd_brl = sgs.get("dolar", start="1984-01-01")

# Multiple series at once
df = sgs.get({"Selic": 11, "IPCA": 433, "USD": 1}, start="2010-01-01")

# Last N values
ipca = sgs.get("ipca", last=12)
```

**Features:**
- Automatic pagination (splits into 10-year chunks, parallel async requests)
- 14 pre-configured series with aliases
- SQLite cache with TTL
- Automatic retry with exponential backoff
- Returns pandas DataFrame
- REST API (FastAPI) and interactive dashboard (Streamlit + Plotly)
- Fully async under the hood (httpx + asyncio)

**Tech stack:** Python 3.10+, httpx, asyncio, FastAPI, Streamlit, Plotly

- GitHub: https://github.com/fmaignacio/bacendata
- PyPI: https://pypi.org/project/bacendata/
- Dashboard: https://bacendata.streamlit.app

Feedback welcome!
