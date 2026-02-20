# Artigo Medium / Dev.to

## Título: Como eu resolvi o limite de 10 anos da API do Banco Central com Python

### Tags: python, opensource, fintech, tutorial

---

Em março de 2025, o Banco Central do Brasil implementou uma mudança silenciosa na API SGS (Sistema Gerenciador de Séries Temporais): consultas passaram a ser limitadas a no máximo 10 anos por requisição.

Para quem trabalha com séries históricas curtas, nada mudou. Mas se você precisa da cotação do Dólar desde 1984, da Selic desde 1986 ou do IPCA desde 1980 — como é comum em análise econômica, modelagem de risco ou estudos acadêmicos — essa limitação se tornou um problema real.

Criei o **BacenData** para resolver isso de forma transparente.

## O problema em detalhes

A API SGS do Banco Central é pública e gratuita. Você faz uma requisição HTTP com o código da série, data inicial e data final, e recebe um JSON com os valores.

Até 2025, era possível consultar qualquer período:

```
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json&dataInicial=01/01/1984&dataFinal=31/12/2025
```

Agora, se o intervalo for maior que 10 anos, a API retorna erro 400 ou uma resposta vazia. Para obter dados completos do Dólar (código 1), que existe desde 1984, você precisaria fazer pelo menos 5 requisições separadas, concatenar os resultados e remover duplicatas.

É exatamente isso que o BacenData automatiza.

## A solução: paginação automática

```python
pip install bacendata
```

```python
from bacendata import sgs

# Série completa do Dólar — 40+ anos em uma chamada
dolar = sgs.get("dolar", start="1984-01-01")
print(f"{len(dolar)} registros de {dolar.index[0]} a {dolar.index[-1]}")
```

Por baixo dos panos, o BacenData:

1. **Calcula os intervalos**: divide o período solicitado em chunks de no máximo 10 anos
2. **Faz requisições paralelas**: usa `asyncio.gather` com um `Semaphore(5)` para limitar a 5 requisições simultâneas (cortesia com o servidor do BACEN)
3. **Combina os resultados**: concatena todos os DataFrames, remove duplicatas de datas sobrepostas e ordena cronologicamente
4. **Trata erros individuais**: se um intervalo retornar 404 (dados não disponíveis naquele período), ele é ignorado sem abortar a consulta inteira

O resultado é um `pandas.DataFrame` limpo, pronto para análise.

## Funcionalidades principais

### 1. Aliases para séries populares

Em vez de decorar códigos numéricos, use nomes:

```python
# Estes são equivalentes:
sgs.get(1, start="2020-01-01")
sgs.get("dolar", start="2020-01-01")
```

O BacenData vem com 14 séries pré-configuradas:

| Alias | Código | Descrição |
|-------|--------|-----------|
| selic | 11 | Taxa Selic diária |
| selic_meta | 432 | Meta Selic definida pelo Copom |
| selic_mensal | 4390 | Selic acumulada no mês |
| ipca | 433 | IPCA variação mensal |
| dolar | 1 | Dólar PTAX venda |
| euro | 21619 | Euro PTAX compra |
| cdi | 12 | CDI diário |
| igpm | 189 | IGP-M variação mensal |
| juros_pf | 20714 | Taxa média de juros PF |
| juros_pj | 20715 | Taxa média de juros PJ |
| inadimplencia_pf | 21112 | Inadimplência PF |
| inadimplencia_pj | 21113 | Inadimplência PJ |
| reservas | 13621 | Reservas internacionais (USD) |
| focus_ipca | 13522 | Expectativa Focus IPCA |

### 2. Múltiplas séries de uma vez

```python
df = sgs.get({"Selic": 11, "IPCA": 433, "Dólar": 1}, start="2015-01-01")
print(df.head())
```

Resultado:

```
                Selic   IPCA  Dólar
data
2015-01-02  0.046189    NaN  2.694
2015-01-05  0.046189    NaN  2.702
...
```

### 3. Últimos N valores

```python
# Últimos 12 valores do IPCA
ipca = sgs.get("ipca", last=12)
```

### 4. Cache inteligente

O BacenData mantém um cache SQLite local com TTL automático por tipo de série:
- Séries diárias: cache de 6 horas
- Séries mensais: cache de 24 horas

```python
# Desativar cache se necessário
from bacendata.wrapper.cache import desativar
desativar()
```

### 5. Metadados das séries

```python
meta = sgs.metadata(1)
print(meta)
# {'codigo': 1, 'nome': 'Taxa de câmbio - Livre - Dólar americano (venda) - diário',
#  'periodicidade': 'D', 'unidade': 'u.m.c./US$', ...}
```

## Como funciona por dentro

A arquitetura é simples e pragmática:

```
bacendata/
├── wrapper/
│   ├── bacen_sgs.py    # Core: get(), aget(), metadata()
│   ├── catalogo.py     # 14 séries pré-configuradas
│   ├── cache.py        # Cache SQLite com TTL
│   └── exceptions.py   # Exceções customizadas
├── api/
│   ├── app.py          # FastAPI app factory
│   └── routes/         # Endpoints REST
└── schemas/
    └── series.py       # Pydantic models
```

### A paginação em detalhe

O coração do BacenData é a função `_buscar_com_paginacao`:

```python
async def _buscar_com_paginacao(codigo, inicio, fim, client):
    intervalos = _gerar_intervalos(inicio, fim, max_anos=10)
    semaforo = asyncio.Semaphore(5)

    async def fetch_com_semaforo(ini, fi):
        async with semaforo:
            try:
                return await _buscar_serie_periodo(codigo, ini, fi, client)
            except (SerieNaoEncontrada, BacenAPIError):
                return []  # Intervalo sem dados, não aborta

    tasks = [fetch_com_semaforo(ini, fi) for ini, fi in intervalos]
    resultados = await asyncio.gather(*tasks)

    todos_dados = [item for sublista in resultados for item in sublista]
    if not todos_dados:
        raise SerieNaoEncontrada(codigo)
    return todos_dados
```

O `Semaphore(5)` é crucial: sem ele, uma consulta de 40 anos geraria 5 requisições simultâneas de uma vez, podendo sobrecarregar o servidor do BACEN. Com o semáforo, nunca passamos de 5 conexões paralelas.

O `try/except` no `fetch_com_semaforo` resolve outro problema sutil: quando o usuário pede "todos os dados disponíveis", o BacenData gera intervalos desde 1960. Para séries que começaram em 1984, os intervalos de 1960-1970 e 1970-1980 retornam 404. Sem o try/except, o `asyncio.gather` falharia inteiramente.

### Stack técnica

- **httpx** (async): HTTP client — escolhido por suporte nativo a async, ao contrário do `requests`
- **asyncio**: paralelismo de I/O para paginação
- **pandas**: retorno em DataFrame para integração fácil com o ecossistema Python de dados
- **SQLite**: cache local leve, sem dependências extras
- **FastAPI**: API REST com docs automáticas (Swagger/ReDoc)
- **Streamlit + Plotly**: dashboard interativo para não-programadores

## API REST

O BacenData também expõe uma API REST para integração com qualquer linguagem/sistema:

```bash
# Instalar
pip install bacendata[api]

# Rodar
uvicorn bacendata.api.app:create_app --factory --port 8000
```

Endpoints:

```
GET /api/v1/series/{codigo}?start=2020-01-01&end=2025-01-01
GET /api/v1/series/{codigo}/metadata
POST /api/v1/series/bulk  (múltiplas séries)
GET /api/v1/catalogo
GET /api/v1/catalogo/search?q=selic
GET /health
```

Exemplo:

```bash
curl "http://localhost:8000/api/v1/series/1?start=2025-01-01&last=5"
```

```json
{
  "codigo": 1,
  "nome": "Taxa de câmbio - Livre - Dólar americano (venda) - diário",
  "dados": [
    {"data": "2025-01-02", "valor": 6.1797},
    {"data": "2025-01-03", "valor": 6.1627},
    ...
  ],
  "total_registros": 5
}
```

## Dashboard interativo

Para quem não programa, o BacenData tem um dashboard Streamlit público:

**https://bacendata.streamlit.app**

Features:
- Gráficos interativos com zoom e hover
- Comparação lado a lado de até 3 séries
- Média móvel configurável
- Download CSV/Excel
- Todos os 14 indicadores disponíveis

## Como contribuir

O projeto é open source (MIT). Algumas ideias para contribuição:

- Adicionar novas séries ao catálogo
- Integrar com a API de expectativas Focus (séries futuras)
- Criar wrappers para R ou JavaScript
- Melhorar a documentação

## Links

- **GitHub**: [github.com/fmaignacio/bacendata](https://github.com/fmaignacio/bacendata)
- **PyPI**: [pypi.org/project/bacendata](https://pypi.org/project/bacendata/)
- **Dashboard**: [bacendata.streamlit.app](https://bacendata.streamlit.app)
- **Site**: [bacendata.com](https://bacendata.com)

---

*Se você trabalha com dados econômicos no Brasil — como economista, analista, desenvolvedor ou pesquisador — o BacenData pode te poupar horas de trabalho manual. Dá uma olhada e me conta o que achou.*
