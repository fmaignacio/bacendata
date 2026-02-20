# Post LinkedIn

## Post 1 — Lançamento

Em março de 2025, o Banco Central limitou a API SGS a consultas de no máximo 10 anos por requisição. Para quem trabalha com séries históricas longas — economistas, analistas de crédito, fintechs — isso virou um problema real.

Criei o BacenData para resolver isso.

O que ele faz:
- Paginação automática: consulte qualquer período em 1 linha de Python, sem se preocupar com o limite de 10 anos
- 14 séries pré-configuradas: Selic, IPCA, câmbio, crédito, inadimplência, reservas e Focus
- Dashboard interativo: gráficos, comparação de séries, download CSV/Excel
- API REST: endpoints JSON para integrar com qualquer sistema

Como usar:

pip install bacendata

from bacendata import sgs
selic = sgs.get("selic", start="2000-01-01")  # 25 anos, sem erro

O projeto é open source e o dashboard está público em bacendata.streamlit.app

Se você trabalha com dados econômicos no Brasil, dá uma olhada. Feedback é bem-vindo.

GitHub: github.com/fmaignacio/bacendata
Dashboard: bacendata.streamlit.app
API Docs: bacendata-production.up.railway.app/docs
Site: bacendata.com

#OpenSource #Python #FinTech #BancoCentral #DataScience #Economia

---

## Post 2 — Técnico (1 semana depois)

Você sabia que a API do Banco Central (SGS) tem um limite de 10 anos por consulta desde março de 2025?

Se você já tentou puxar a série histórica completa do Dólar (desde 1984) ou da Selic (desde 1986), sabe a dor: erro 400, resposta vazia, frustração.

O BacenData resolve com 3 linhas:

from bacendata import sgs
dolar = sgs.get("dolar", start="1984-01-01")
print(f"{len(dolar)} registros em {dolar.index[0]} a {dolar.index[-1]}")

Por baixo, ele divide a consulta em chunks de 10 anos, faz requisições paralelas com semáforo (máx 5 simultâneas), e combina tudo em um DataFrame pandas — com deduplicação e ordenação automática.

Stack:
- httpx (async) para HTTP
- asyncio.gather + Semaphore para paralelismo controlado
- Cache SQLite local com TTL por periodicidade
- FastAPI para a API REST
- Streamlit + Plotly para o dashboard

GitHub: github.com/fmaignacio/bacendata
API ao vivo: bacendata-production.up.railway.app/docs

#Python #AsyncIO #FastAPI #DataEngineering #FinTech
