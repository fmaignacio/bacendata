# BacenData

Acesso simplificado aos dados do Banco Central do Brasil.

Resolve automaticamente a limitacao de 10 anos por consulta imposta pelo BACEN em marco/2025, com paginacao transparente, retry inteligente e cache local.

## Instalacao

```bash
pip install bacendata
```

## Uso rapido

```python
from bacendata import sgs

# Buscar a taxa Selic (por codigo ou nome)
selic = sgs.get(11, start="2020-01-01")
selic = sgs.get("selic", start="2020-01-01")

# Buscar multiplas series de uma vez
df = sgs.get({"Selic": 11, "IPCA": 433, "Dolar": 1}, start="2010-01-01")

# Ultimos N valores
ipca = sgs.get(433, last=12)

# Buscar mais de 10 anos (paginacao automatica!)
selic_longa = sgs.get(11, start="2000-01-01", end="2024-12-31")
```

## Funcionalidades

- **Paginacao automatica** — consultas >10 anos sao divididas em chunks e feitas em paralelo
- **Multiplas series** — busque varias series de uma vez com `dict`
- **Catalogo integrado** — use nomes em vez de codigos: `sgs.get("selic")`
- **Cache local** — evite chamadas repetidas a API do BACEN
- **Retry com backoff** — trata automaticamente erros 429, 500 e timeouts
- **Formato flexivel** — aceita datas ISO (`2024-01-01`), brasileiro (`01/01/2024`) e objetos `date`
- **Retorno pandas** — dados prontos para analise como `DataFrame`
- **Async nativo** — interface sync (`get`) e async (`aget`) para FastAPI

## Catalogo de series

Voce pode usar nomes em vez de codigos numericos:

```python
sgs.get("selic")          # Taxa Selic diaria (codigo 11)
sgs.get("ipca")           # IPCA mensal (codigo 433)
sgs.get("dolar")          # Dolar PTAX compra (codigo 1)
sgs.get("euro")           # Euro compra PTAX (codigo 21619)
sgs.get("euro")           # Euro compra (codigo 10813)
sgs.get("focus_ipca")     # Expectativa IPCA 12m (codigo 27574)
sgs.get("focus_selic")    # Expectativa Selic (codigo 27575)
sgs.get("inadimplencia_pf")  # Inadimplencia PF (codigo 21112)
```

Para listar todas as series disponiveis:

```python
from bacendata.wrapper.catalogo import listar

for serie in listar():
    print(f"{serie.codigo:>6} | {serie.nome} ({serie.periodicidade})")
```

## Cache local

Ative o cache para evitar chamadas repetidas:

```python
from bacendata import sgs

sgs.cache.ativar()  # Salva em ~/.bacendata/cache.db

selic = sgs.get(11, start="2020-01-01")  # Primeira vez: busca na API
selic = sgs.get(11, start="2020-01-01")  # Segunda vez: le do cache

# Caminho customizado
sgs.cache.ativar("/tmp/meu_cache.db")

# Limpar cache
sgs.cache.limpar()

# Desativar
sgs.cache.desativar()
```

TTL padrao por periodicidade:
- Series diarias: 1 hora
- Series semanais: 6 horas
- Series mensais: 24 horas

## Metadados

```python
info = sgs.metadata(433)
# {'codigo': 433, 'nome': 'IPCA - Variacao mensal', 'periodicidade': 'Mensal', ...}
```

## Interface async

Para uso em FastAPI ou outros frameworks async:

```python
import asyncio
from bacendata import sgs

async def main():
    df = await sgs.aget(11, start="2020-01-01")
    print(df)

asyncio.run(main())
```

## Series disponiveis no catalogo

| Codigo | Nome | Periodicidade | Aliases |
|--------|------|---------------|---------|
| 1 | Dolar (compra) | Diaria | `dolar`, `usd`, `ptax`, `cambio` |
| 11 | Selic diaria | Diaria | `selic`, `selic_diaria` |
| 12 | Selic acumulada no mes | Mensal | `selic_mensal`, `selic_acumulada` |
| 433 | IPCA | Mensal | `ipca`, `inflacao` |
| 4189 | Juros PF | Mensal | `juros_pf`, `taxa_pf` |
| 4390 | Selic acumulada anualizada | Mensal | `selic_anual`, `selic_anualizada` |
| 7326 | Reservas Internacionais | Diaria | `reservas` |
| 21619 | Euro (compra) PTAX | Diaria | `euro`, `eur` |
| 10813 | Euro (compra) | Diaria | `euro`, `eur` |
| 20542 | Saldo Credito Livre | Mensal | `saldo_credito`, `carteira_credito` |
| 21082 | Inadimplencia PJ | Mensal | `inadimplencia_pj`, `default_pj` |
| 21112 | Inadimplencia PF | Mensal | `inadimplencia_pf`, `default_pf` |
| 25434 | Juros Credito Livre | Mensal | `juros_credito`, `credito_livre` |
| 27574 | Expectativa IPCA 12m | Semanal | `focus_ipca`, `expectativa_ipca` |
| 27575 | Expectativa Selic | Semanal | `focus_selic`, `expectativa_selic` |

Qualquer codigo SGS funciona mesmo fora do catalogo: `sgs.get(99999, last=10)`.

## Tratamento de erros

```python
from bacendata.wrapper.exceptions import (
    SerieNaoEncontrada,
    BacenAPIError,
    BacenTimeoutError,
    ParametrosInvalidos,
)

try:
    df = sgs.get(99999, start="2024-01-01")
except SerieNaoEncontrada:
    print("Serie nao existe")
except BacenTimeoutError:
    print("API do BACEN nao respondeu")
except BacenAPIError as e:
    print(f"Erro {e.status_code}: {e.mensagem}")
```

## Desenvolvimento

```bash
git clone https://github.com/fmaignacio/bacendata.git
cd bacendata
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -e ".[dev]"

# Testes
python -m pytest tests/ -v --cov=src/bacendata

# Lint
ruff check src/ tests/
black src/ tests/
```

## Licenca

MIT
