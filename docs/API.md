# BacenData API — Documentacao Tecnica

> **Versao:** 0.2.0 | **Base URL:** `http://localhost:8000` | **Docs interativas:** `/docs` (Swagger) ou `/redoc`

## Indice

1. [Visao Geral](#1-visao-geral)
2. [Instalacao e Setup](#2-instalacao-e-setup)
3. [Autenticacao](#3-autenticacao)
4. [Rate Limiting](#4-rate-limiting)
5. [Endpoints](#5-endpoints)
   - 5.1 [Health Check](#51-health-check)
   - 5.2 [Consultar Serie](#52-consultar-serie)
   - 5.3 [Metadados da Serie](#53-metadados-da-serie)
   - 5.4 [Consulta Bulk](#54-consulta-bulk-multiplas-series)
   - 5.5 [Catalogo de Series](#55-catalogo-de-series)
   - 5.6 [Buscar no Catalogo](#56-buscar-no-catalogo)
6. [Catalogo Completo de Series](#6-catalogo-completo-de-series)
7. [Wrapper Python (Biblioteca)](#7-wrapper-python-biblioteca)
8. [Formatos de Data](#8-formatos-de-data)
9. [Codigos de Erro](#9-codigos-de-erro)
10. [Configuracao do Servidor](#10-configuracao-do-servidor)
11. [Exemplos Praticos por Perfil](#11-exemplos-praticos-por-perfil)

---

## 1. Visao Geral

A **BacenData API** e uma interface REST moderna que simplifica o acesso aos dados do **Sistema Gerenciador de Series Temporais (SGS)** do Banco Central do Brasil.

### Problemas que a API resolve

| Problema | Solucao BacenData |
|----------|------------------|
| API do BACEN limita consultas a 10 anos (desde marco/2025) | Paginacao automatica transparente — consulte 25, 30, 50 anos de uma vez |
| Necessidade de montar URLs manualmente com parametros complexos | Endpoints simples: `/api/v1/series/11` ou `/api/v1/series/selic` |
| Buscar multiplas series exige multiplas chamadas | Endpoint `/api/v1/series/bulk` busca ate 20 series em uma requisicao |
| Nao existe catalogo amigavel das series mais usadas | Catalogo de 14 series com aliases (ex: `selic`, `ipca`, `dolar`) |
| Erros silenciosos e dados inconsistentes | Retry automatico, tratamento de erros, dados sempre validados |
| Sem cache — toda consulta vai ao BACEN | Cache local inteligente com TTL por periodicidade |

### Stack tecnica

- **FastAPI** (Python 3.11+) — Framework async de alta performance
- **httpx** — Cliente HTTP assincrono para chamadas ao BACEN
- **Pydantic** — Validacao de dados e schemas tipados
- **pydantic-settings** — Configuracao via variaveis de ambiente
- **SQLite** — Cache local com TTL por periodicidade

---

## 2. Instalacao e Setup

### Pre-requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes)

### Instalacao

```bash
# Instalar o pacote com dependencias da API
pip install bacendata
pip install "bacendata[api]"

# OU clonar o repositorio
git clone https://github.com/fmaignacio/bacendata.git
cd bacendata
pip install -e ".[api]"
```

### Iniciar o servidor

```bash
# Modo desenvolvimento (com reload automatico)
uvicorn bacendata.api.app:create_app --factory --reload --port 8000

# Modo producao
uvicorn bacendata.api.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 4
```

### Verificar se esta funcionando

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{
  "status": "ok",
  "versao": "0.2.0",
  "servico": "BacenData API"
}
```

Acesse `http://localhost:8000/docs` no navegador para a documentacao interativa (Swagger UI).

---

## 3. Autenticacao

A API suporta autenticacao por **API key** via header HTTP.

### Header

```
X-API-Key: sua-chave-aqui
```

### Comportamento

| Cenario | Resultado |
|---------|-----------|
| Nenhuma API key configurada no servidor | Acesso livre (plano free) |
| API key valida enviada | Acesso com plano correspondente (free ou pro) |
| API key invalida enviada | Erro 401 |
| Nenhuma API key enviada (com keys configuradas) | Acesso como free |

### Exemplo com cURL

```bash
# Sem autenticacao (plano free)
curl http://localhost:8000/api/v1/series/11?start=2024-01-01&end=2024-12-31

# Com API key
curl -H "X-API-Key: minha-chave-pro" \
     http://localhost:8000/api/v1/series/11?start=2024-01-01&end=2024-12-31
```

### Exemplo com Python

```python
import httpx

# Sem autenticacao
response = httpx.get("http://localhost:8000/api/v1/series/11", params={"start": "2024-01-01"})

# Com API key
response = httpx.get(
    "http://localhost:8000/api/v1/series/11",
    params={"start": "2024-01-01"},
    headers={"X-API-Key": "minha-chave-pro"}
)
```

### Configurar API keys no servidor

Defina a variavel de ambiente `BACENDATA_API_KEYS` no formato `chave:plano,chave:plano`:

```bash
export BACENDATA_API_KEYS="abc123:free,xyz789:pro,minha-chave-enterprise:pro"
```

Ou no arquivo `.env`:

```env
BACENDATA_API_KEYS=abc123:free,xyz789:pro
```

---

## 4. Rate Limiting

Cada requisicao retorna headers informando seu consumo:

| Header | Descricao |
|--------|-----------|
| `X-RateLimit-Limit` | Limite total de requisicoes por dia |
| `X-RateLimit-Remaining` | Requisicoes restantes na janela atual |
| `Retry-After` | Segundos ate a janela resetar (so quando excedido) |

### Limites por plano

| Plano | Limite | Identificacao |
|-------|--------|---------------|
| **Free** (sem API key) | 100 req/dia | Por IP |
| **Pro** (com API key) | 10.000 req/dia | Por API key |

### Resposta quando excedido (HTTP 429)

```json
{
  "erro": "Limite de requisicoes excedido.",
  "detalhe": "Limite: 100 req/dia. Tente novamente em 43200s. Para mais requisicoes, use uma API key Pro."
}
```

### Endpoints isentos de rate limiting

- `GET /health`
- `GET /docs`
- `GET /redoc`
- `GET /openapi.json`

---

## 5. Endpoints

### 5.1 Health Check

Verifica se a API esta funcionando.

**`GET /health`**

**Resposta (200):**

```json
{
  "status": "ok",
  "versao": "0.2.0",
  "servico": "BacenData API"
}
```

---

### 5.2 Consultar Serie

Busca dados de uma serie temporal do BACEN SGS.

**`GET /api/v1/series/{codigo}`**

#### Parametros de caminho (path)

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `codigo` | `int` ou `string` | Codigo SGS numerico (ex: `11`) ou nome do catalogo (ex: `selic`) |

#### Parametros de consulta (query)

| Parametro | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `start` | `string` | Nao* | Data inicial (`YYYY-MM-DD` ou `DD/MM/YYYY`) |
| `end` | `string` | Nao | Data final (`YYYY-MM-DD` ou `DD/MM/YYYY`). Padrao: hoje |
| `last` | `int` | Nao* | Ultimos N valores (ignora start/end) |

> *Pelo menos `start` ou `last` deve ser informado. Se nenhum for passado, retorna os ultimos 10 anos.

#### Exemplo: buscar Selic por codigo

```bash
curl "http://localhost:8000/api/v1/series/11?start=2024-01-01&end=2024-06-30"
```

#### Exemplo: buscar Selic por nome

```bash
curl "http://localhost:8000/api/v1/series/selic?start=2024-01-01&end=2024-06-30"
```

#### Exemplo: ultimos 5 valores do IPCA

```bash
curl "http://localhost:8000/api/v1/series/433?last=5"
```

#### Exemplo: buscar dolar usando alias

```bash
curl "http://localhost:8000/api/v1/series/dolar?start=2024-01-01"
```

#### Resposta (200)

```json
{
  "codigo": 11,
  "nome": "Selic diaria",
  "periodicidade": "diaria",
  "unidade": "% a.a.",
  "dados": [
    {"data": "02/01/2024", "valor": 11.65},
    {"data": "03/01/2024", "valor": 11.65},
    {"data": "04/01/2024", "valor": 11.65}
  ],
  "total": 3
}
```

#### Respostas de erro

| Status | Situacao |
|--------|---------|
| 400 | Parametros invalidos (data inicio > data fim, nome inexistente no catalogo) |
| 404 | Serie nao encontrada na API do BACEN |
| 502 | Erro ou timeout na API do BACEN |

---

### 5.3 Metadados da Serie

Retorna informacoes sobre uma serie (nome completo, periodicidade, fonte, etc).

**`GET /api/v1/series/{codigo}/metadata`**

#### Parametros

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `codigo` | `int` | Codigo SGS da serie |

#### Exemplo

```bash
curl "http://localhost:8000/api/v1/series/433/metadata"
```

#### Resposta (200)

```json
{
  "codigo": 433,
  "nome": "IPCA - Variacao mensal",
  "unidade": "% a.m.",
  "periodicidade": "Mensal",
  "fonte": "IBGE",
  "inicio": "01/01/1980",
  "fim": "01/01/2025"
}
```

---

### 5.4 Consulta Bulk (Multiplas Series)

Busca ate **20 series** em uma unica requisicao.

**`POST /api/v1/series/bulk`**

#### Corpo da requisicao (JSON)

```json
{
  "series": [
    {"codigo": 11, "nome": "Selic"},
    {"codigo": 433, "nome": "IPCA"},
    {"codigo": 1, "nome": "Dolar"}
  ],
  "start": "2024-01-01",
  "end": "2024-12-31",
  "last": null
}
```

| Campo | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| `series` | `array` | Sim | Lista de 1 a 20 series |
| `series[].codigo` | `int` ou `string` | Sim | Codigo SGS ou nome do catalogo |
| `series[].nome` | `string` | Nao | Rotulo para identificar a serie no resultado |
| `start` | `string` | Nao | Data inicial |
| `end` | `string` | Nao | Data final |
| `last` | `int` | Nao | Ultimos N valores |

#### Exemplo com cURL

```bash
curl -X POST http://localhost:8000/api/v1/series/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "series": [
      {"codigo": 11, "nome": "Selic"},
      {"codigo": 433, "nome": "IPCA"},
      {"codigo": "dolar", "nome": "USD/BRL"}
    ],
    "start": "2024-01-01",
    "end": "2024-12-31"
  }'
```

#### Exemplo com Python

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/series/bulk",
    json={
        "series": [
            {"codigo": 11, "nome": "Selic"},
            {"codigo": 433, "nome": "IPCA"},
            {"codigo": "dolar", "nome": "USD/BRL"},
        ],
        "start": "2024-01-01",
        "end": "2024-12-31",
    }
)
data = response.json()
for serie in data["series"]:
    print(f"{serie['nome']}: {serie['total']} registros")
```

#### Resposta (200)

```json
{
  "series": [
    {
      "codigo": 11,
      "nome": "Selic",
      "dados": [
        {"data": "02/01/2024", "valor": 11.65},
        {"data": "03/01/2024", "valor": 11.65}
      ],
      "total": 248
    },
    {
      "codigo": 433,
      "nome": "IPCA",
      "dados": [
        {"data": "01/01/2024", "valor": 0.42},
        {"data": "01/02/2024", "valor": 0.83}
      ],
      "total": 12
    },
    {
      "codigo": 1,
      "nome": "USD/BRL",
      "dados": [
        {"data": "02/01/2024", "valor": 4.8878}
      ],
      "total": 248
    }
  ],
  "total_series": 3
}
```

#### Validacoes

| Regra | Erro |
|-------|------|
| Lista vazia | HTTP 422 |
| Mais de 20 series | HTTP 422 |
| Serie inexistente no bulk | Retorna com `dados: [], total: 0` (nao bloqueia as demais) |

---

### 5.5 Catalogo de Series

Lista todas as 14 series disponiveis no catalogo com seus aliases.

**`GET /api/v1/catalogo`**

#### Exemplo

```bash
curl http://localhost:8000/api/v1/catalogo
```

#### Resposta (200)

```json
{
  "series": [
    {
      "codigo": 1,
      "nome": "Dolar (compra)",
      "descricao": "Taxa de cambio - Dolar americano (compra) - PTAX",
      "periodicidade": "diaria",
      "unidade": "R$/US$",
      "aliases": ["dolar", "usd", "ptax", "cambio"]
    },
    {
      "codigo": 11,
      "nome": "Selic diaria",
      "descricao": "Taxa de juros Selic diaria",
      "periodicidade": "diaria",
      "unidade": "% a.a.",
      "aliases": ["selic", "selic_diaria"]
    }
  ],
  "total": 14
}
```

---

### 5.6 Buscar no Catalogo

Busca series por nome, descricao ou alias.

**`GET /api/v1/catalogo/search?q={termo}`**

#### Parametros

| Parametro | Tipo | Obrigatorio | Descricao |
|-----------|------|-------------|-----------|
| `q` | `string` | Sim | Termo de busca (minimo 1 caractere, case-insensitive) |

#### Exemplos

```bash
# Buscar por "selic" — retorna Selic diaria, Selic acumulada, Selic anualizada, Focus Selic
curl "http://localhost:8000/api/v1/catalogo/search?q=selic"

# Buscar por "credito" — retorna Juros Credito Livre, Saldo Credito
curl "http://localhost:8000/api/v1/catalogo/search?q=credito"

# Buscar por "dolar" — retorna Dolar (compra)
curl "http://localhost:8000/api/v1/catalogo/search?q=dolar"

# Busca sem resultado
curl "http://localhost:8000/api/v1/catalogo/search?q=bitcoin"
# Retorna: {"series": [], "total": 0}
```

---

## 6. Catalogo Completo de Series

As 14 series abaixo estao pre-configuradas no catalogo e podem ser acessadas por **codigo numerico**, **nome** ou **alias**:

### Taxas de Juros

| Codigo | Nome | Aliases | Period. | Unidade | Descricao |
|--------|------|---------|---------|---------|-----------|
| 11 | Selic diaria | `selic`, `selic_diaria` | Diaria | % a.a. | Taxa basica de juros da economia brasileira |
| 12 | Selic acumulada no mes | `selic_mensal`, `selic_acumulada` | Mensal | % a.m. | Selic acumulada no mes corrente |
| 4390 | Selic acumulada anualizada | `selic_anual`, `selic_anualizada` | Mensal | % a.a. | Meta Selic anualizada |
| 4189 | Juros PF | `juros_pf`, `taxa_pf` | Mensal | % a.a. | Taxa media de juros cobrada de pessoa fisica |
| 25434 | Juros Credito Livre | `juros_credito`, `credito_livre` | Mensal | % a.a. | Taxa media do credito livre total |

### Inflacao

| Codigo | Nome | Aliases | Period. | Unidade | Descricao |
|--------|------|---------|---------|---------|-----------|
| 433 | IPCA | `ipca`, `inflacao` | Mensal | % a.m. | Indice Nacional de Precos ao Consumidor Amplo |

### Cambio

| Codigo | Nome | Aliases | Period. | Unidade | Descricao |
|--------|------|---------|---------|---------|-----------|
| 1 | Dolar (compra) | `dolar`, `usd`, `ptax`, `cambio` | Diaria | R$/US$ | Taxa PTAX de compra do dolar |
| 21619 | Euro (compra) PTAX | `euro`, `eur` | Diaria | R$/EUR | Taxa PTAX de compra do euro |
| 10813 | Euro (compra) | `euro`, `eur` | Diaria | R$/EUR | Taxa de compra do euro |

### Credito

| Codigo | Nome | Aliases | Period. | Unidade | Descricao |
|--------|------|---------|---------|---------|-----------|
| 20542 | Saldo Credito Livre | `saldo_credito`, `carteira_credito` | Mensal | R$ milhoes | Carteira total de credito livre |
| 21112 | Inadimplencia PF | `inadimplencia_pf`, `default_pf` | Mensal | % | Inadimplencia pessoa fisica |
| 21082 | Inadimplencia PJ | `inadimplencia_pj`, `default_pj` | Mensal | % | Inadimplencia pessoa juridica |

### Setor Externo

| Codigo | Nome | Aliases | Period. | Unidade | Descricao |
|--------|------|---------|---------|---------|-----------|
| 7326 | Reservas Internacionais | `reservas`, `reservas_internacionais` | Diaria | US$ milhoes | Reservas internacionais (liquidez) |

### Expectativas (Focus)

| Codigo | Nome | Aliases | Period. | Unidade | Descricao |
|--------|------|---------|---------|---------|-----------|
| 27574 | Expectativa IPCA 12m | `focus_ipca`, `expectativa_ipca` | Semanal | % a.a. | Mediana Focus para IPCA 12 meses |
| 27575 | Expectativa Selic | `focus_selic`, `expectativa_selic` | Semanal | % a.a. | Mediana Focus para a Selic |

### Series fora do catalogo

A API aceita **qualquer codigo SGS valido**, nao apenas os 14 do catalogo. Para series fora do catalogo, use o codigo numerico diretamente:

```bash
# CDI (codigo 4389)
curl "http://localhost:8000/api/v1/series/4389?start=2024-01-01"

# PIB trimestral (codigo 22109)
curl "http://localhost:8000/api/v1/series/22109?last=8"
```

---

## 7. Wrapper Python (Biblioteca)

Alem da API REST, o BacenData pode ser usado diretamente como biblioteca Python:

```bash
pip install bacendata
```

### Uso basico

```python
from bacendata import sgs

# Por codigo
selic = sgs.get(11, start="2024-01-01")

# Por nome do catalogo
ipca = sgs.get("ipca", last=12)

# Multiplas series
df = sgs.get({"Selic": 11, "IPCA": 433, "Dolar": 1}, start="2020-01-01")

# Paginacao automatica (>10 anos)
historico = sgs.get(11, start="2000-01-01", end="2024-12-31")
print(f"25 anos de Selic: {len(historico)} registros")

# Cache local
sgs.cache.ativar()
selic = sgs.get(11, start="2024-01-01")  # Busca na API
selic = sgs.get(11, start="2024-01-01")  # Instantaneo (cache)

# Metadados
info = sgs.metadata(433)
print(info["nome"])  # "IPCA - Variacao mensal"

# Listar catalogo
for serie in sgs.catalogo.listar():
    print(f"{serie.codigo}: {serie.nome} ({serie.periodicidade})")
```

### Interface async (para FastAPI, frameworks async)

```python
import asyncio
from bacendata import sgs

async def main():
    df = await sgs.aget(11, start="2024-01-01")
    meta = await sgs.ametadata(433)
    print(df)

asyncio.run(main())
```

### Retorno sempre como pandas DataFrame

```python
df = sgs.get("selic", start="2024-01-01")
print(type(df))       # <class 'pandas.core.frame.DataFrame'>
print(df.columns)     # Index(['valor'], dtype='object')
print(df.index.name)  # 'data'

# Facil de exportar
df.to_csv("selic_2024.csv")
df.to_excel("selic_2024.xlsx")

# Facil de plotar
df["valor"].plot(title="Selic 2024", figsize=(12, 6))
```

---

## 8. Formatos de Data

A API aceita datas em dois formatos:

| Formato | Exemplo | Padrao |
|---------|---------|--------|
| ISO 8601 | `2024-01-15` | Internacional |
| Brasileiro | `15/01/2024` | BR |

As datas nas **respostas** sempre vem no formato brasileiro (`DD/MM/YYYY`), conforme padrao da API SGS.

### Comportamento padrao

| Situacao | Comportamento |
|----------|---------------|
| `start` e `end` informados | Retorna dados no intervalo |
| Apenas `start` | Retorna de `start` ate hoje |
| Apenas `end` | Retorna 10 anos antes de `end` ate `end` |
| Nenhum (sem `last`) | Retorna ultimos 10 anos |
| `last=N` | Retorna ultimos N valores (ignora start/end) |

---

## 9. Codigos de Erro

| HTTP | Significado | Quando ocorre |
|------|-------------|---------------|
| 200 | Sucesso | Dados retornados com sucesso |
| 400 | Bad Request | Parametros invalidos (data_inicio > data_fim, nome nao encontrado) |
| 401 | Unauthorized | API key invalida |
| 404 | Not Found | Serie SGS nao existe na API do BACEN |
| 422 | Unprocessable Entity | Corpo da requisicao invalido (bulk vazio, >20 series) |
| 429 | Too Many Requests | Rate limit excedido |
| 502 | Bad Gateway | API do BACEN indisponivel, timeout, ou erro interno do BACEN |

### Formato de erro

```json
{
  "detail": "Serie 99999 nao encontrada na API do BACEN."
}
```

Para erros de rate limiting:

```json
{
  "erro": "Limite de requisicoes excedido.",
  "detalhe": "Limite: 100 req/dia. Tente novamente em 43200s."
}
```

---

## 10. Configuracao do Servidor

Todas as configuracoes sao feitas via variaveis de ambiente com prefixo `BACENDATA_`:

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `BACENDATA_APP_NAME` | `BacenData API` | Nome da aplicacao |
| `BACENDATA_APP_VERSION` | `0.2.0` | Versao exibida |
| `BACENDATA_DEBUG` | `false` | Modo debug |
| `BACENDATA_RATE_LIMIT_FREE` | `100` | Req/dia para plano free |
| `BACENDATA_RATE_LIMIT_PRO` | `10000` | Req/dia para plano pro |
| `BACENDATA_API_KEYS` | *(vazio)* | API keys no formato `chave:plano,chave:plano` |
| `BACENDATA_BACEN_MAX_CONCURRENT` | `5` | Max requisicoes simultaneas ao BACEN |
| `BACENDATA_BACEN_TIMEOUT` | `30` | Timeout em segundos por requisicao |
| `BACENDATA_CACHE_ATIVO` | `true` | Ativar cache local SQLite |

### Exemplo de .env

```env
BACENDATA_DEBUG=false
BACENDATA_RATE_LIMIT_FREE=100
BACENDATA_RATE_LIMIT_PRO=10000
BACENDATA_API_KEYS=demo-key-123:free,pro-key-abc:pro
BACENDATA_CACHE_ATIVO=true
```

---

## 11. Exemplos Praticos por Perfil

### Para o economista: acompanhar inflacao e juros

```bash
# IPCA dos ultimos 24 meses
curl "http://localhost:8000/api/v1/series/ipca?last=24"

# Expectativa Focus para IPCA e Selic
curl -X POST http://localhost:8000/api/v1/series/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "series": [
      {"codigo": "focus_ipca", "nome": "Expectativa IPCA"},
      {"codigo": "focus_selic", "nome": "Expectativa Selic"}
    ],
    "last": 52
  }'
```

### Para o analista de credito: monitorar inadimplencia

```bash
# Inadimplencia PF e PJ dos ultimos 5 anos
curl -X POST http://localhost:8000/api/v1/series/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "series": [
      {"codigo": "inadimplencia_pf", "nome": "PF"},
      {"codigo": "inadimplencia_pj", "nome": "PJ"},
      {"codigo": "saldo_credito", "nome": "Carteira"}
    ],
    "start": "2020-01-01"
  }'
```

### Para a fintech: monitorar cambio

```python
import httpx

# Ultimos 30 dias de dolar e euro
resp = httpx.post(
    "http://localhost:8000/api/v1/series/bulk",
    json={
        "series": [
            {"codigo": "dolar", "nome": "USD"},
            {"codigo": "euro", "nome": "EUR"},
        ],
        "last": 30,
    }
)
dados = resp.json()
for serie in dados["series"]:
    ultimos = serie["dados"][-1]
    print(f"{serie['nome']}: R$ {ultimos['valor']:.4f} em {ultimos['data']}")
```

### Para o pesquisador: series historicas longas

```python
from bacendata import sgs

# Selic desde 1986 (quase 40 anos — paginacao automatica)
selic = sgs.get(11, start="1986-06-01", end="2024-12-31")
print(f"Total de registros: {len(selic)}")

# Exportar para Excel
selic.to_excel("selic_historico_completo.xlsx")
```

### Para o desenvolvedor: integrar no seu app

```python
import httpx

API_URL = "http://localhost:8000/api/v1"
API_KEY = "sua-chave-pro"

def buscar_selic_atual():
    """Retorna a Selic mais recente."""
    resp = httpx.get(
        f"{API_URL}/series/selic",
        params={"last": 1},
        headers={"X-API-Key": API_KEY},
    )
    resp.raise_for_status()
    dados = resp.json()
    return dados["dados"][0]["valor"]

print(f"Selic atual: {buscar_selic_atual()}% a.a.")
```

---

## Notas Tecnicas

### Paginacao automatica

Quando o periodo solicitado excede 10 anos, a API divide automaticamente em chunks de 10 anos e faz requisicoes paralelas ao BACEN (maximo 5 simultaneas). O resultado e consolidado, deduplicado e ordenado por data.

### Cache

O cache SQLite armazena respostas da API do BACEN com TTL variavel:

| Periodicidade | TTL |
|---------------|-----|
| Diaria | 1 hora |
| Semanal | 6 horas |
| Mensal | 24 horas |

### Retry automatico

Requisicoes que falham com erro 429 (rate limit do BACEN), 500+ (erro do servidor) ou timeout sao automaticamente reenviadas ate 3 vezes, com backoff de 1s, 2s e 5s.

### Limites

| Recurso | Limite |
|---------|--------|
| Series por bulk | 20 |
| Requisicoes simultaneas ao BACEN | 5 |
| Timeout por requisicao | 30s |
| Retries por requisicao | 3 |
