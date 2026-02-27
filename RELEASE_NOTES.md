## v0.2.0 — Primeira versão pública

Primeira release estável da biblioteca **bacendata** para acesso simplificado aos dados do Banco Central do Brasil via API SGS.

### Novidades

- **Consulta de séries temporais** — Use `sgs.get()` para buscar uma ou múltiplas séries do SGS com uma única chamada
- **Paginação automática** — Trata automaticamente a limitação de 10 anos por requisição imposta pelo Banco Central em março/2025, dividindo consultas longas em janelas menores
- **Requisições assíncronas** — Suporte a chamadas concorrentes para consultas com múltiplas séries ou períodos longos
- **Retries com backoff** — Resiliência contra falhas temporárias da API do BCB
- **Cache local** — Evita requisições repetidas para os mesmos dados
- **Catálogo de séries** — Consulte metadados das séries disponíveis no SGS
- **Exceções customizadas** — Erros claros e específicos: `SerieNaoEncontrada`, `BacenAPIError`, `BacenTimeoutError`, `ParametrosInvalidos`
- **Retorno em DataFrame** — Resultados prontos para análise com pandas

### Exemplo de uso

```python
from bacendata import sgs

# Série única
selic = sgs.get(11, start="2020-01-01")

# Múltiplas séries
df = sgs.get({"Selic": 11, "IPCA": 433}, start="2010-01-01")
```

### Requisitos

- Python >= 3.10
- httpx, pandas
