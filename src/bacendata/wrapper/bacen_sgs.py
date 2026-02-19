"""
bacendata.wrapper.bacen_sgs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cliente para a API SGS do Banco Central do Brasil.
Trata automaticamente as limitações de consulta impostas em março/2025.

Uso:
    >>> from bacendata import sgs
    >>> selic = sgs.get(11, start="2020-01-01")
    >>> df = sgs.get({"Selic": 11, "IPCA": 433}, start="2010-01-01")
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import httpx
import pandas as pd

from bacendata.wrapper import cache, catalogo
from bacendata.wrapper.exceptions import (
    BacenAPIError,
    BacenTimeoutError,
    ParametrosInvalidos,
    SerieNaoEncontrada,
)

logger = logging.getLogger("bacendata")

# Constantes
BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
ULTIMOS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}"
MAX_YEARS_PER_REQUEST = 10
MAX_CONCURRENT_REQUESTS = 5
DEFAULT_TIMEOUT = 30  # segundos
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 5]  # segundos entre retries
BACEN_DATE_FORMAT = "%d/%m/%Y"


def _parse_date(valor: Union[str, date, datetime, None]) -> Optional[date]:
    """Converte string ou datetime para date.

    Aceita formatos ISO (YYYY-MM-DD) e brasileiro (DD/MM/YYYY).
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    # Tenta ISO primeiro, depois formato brasileiro
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    raise ParametrosInvalidos(f"Formato de data inválido: '{valor}'. Use YYYY-MM-DD ou DD/MM/YYYY.")


def _gerar_intervalos(
    inicio: date, fim: date, anos_max: int = MAX_YEARS_PER_REQUEST
) -> List[Tuple[date, date]]:
    """Divide um intervalo de datas em chunks de no máximo `anos_max` anos.

    Necessário porque a API do BACEN limita consultas a 10 anos desde março/2025.
    """
    intervalos: List[Tuple[date, date]] = []
    cursor = inicio
    while cursor < fim:
        proximo = min(
            date(cursor.year + anos_max, cursor.month, cursor.day) - timedelta(days=1),
            fim,
        )
        intervalos.append((cursor, proximo))
        cursor = proximo + timedelta(days=1)
    return intervalos


async def _fetch_com_retry(
    client: httpx.AsyncClient,
    url: str,
    params: Dict[str, str],
    codigo: int,
) -> List[Dict[str, str]]:
    """Faz requisição à API do BACEN com retry e backoff exponencial.

    Retorna lista de dicts com campos 'data' e 'valor' da API.
    """
    last_exception: Optional[Exception] = None
    for tentativa in range(MAX_RETRIES):
        try:
            response = await client.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 404:
                raise SerieNaoEncontrada(codigo)

            if response.status_code == 400:
                raise BacenAPIError(400, response.text)

            if response.status_code == 429:
                backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
                logger.warning("Rate limit (429) na série %d. Aguardando %ds...", codigo, backoff)
                await asyncio.sleep(backoff)
                continue

            if response.status_code >= 500:
                backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
                logger.warning(
                    "Erro %d na série %d. Retry %d/%d em %ds...",
                    response.status_code,
                    codigo,
                    tentativa + 1,
                    MAX_RETRIES,
                    backoff,
                )
                await asyncio.sleep(backoff)
                continue

            response.raise_for_status()

            dados = response.json()
            if not isinstance(dados, list):
                return []
            return dados

        except httpx.TimeoutException:
            last_exception = BacenTimeoutError(codigo, tentativa + 1)
            backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
            logger.warning(
                "Timeout na série %d. Retry %d/%d em %ds...",
                codigo,
                tentativa + 1,
                MAX_RETRIES,
                backoff,
            )
            await asyncio.sleep(backoff)
        except (SerieNaoEncontrada, BacenAPIError, ParametrosInvalidos):
            raise
        except httpx.HTTPStatusError as e:
            last_exception = BacenAPIError(e.response.status_code, str(e))
            backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
            await asyncio.sleep(backoff)

    if last_exception:
        raise last_exception
    raise BacenTimeoutError(codigo, MAX_RETRIES)


async def _buscar_serie_periodo(
    client: httpx.AsyncClient,
    codigo: int,
    inicio: date,
    fim: date,
) -> List[Dict[str, str]]:
    """Busca uma série para um período específico (máx 10 anos)."""
    param_inicio = inicio.strftime(BACEN_DATE_FORMAT)
    param_fim = fim.strftime(BACEN_DATE_FORMAT)

    # Tentar cache primeiro
    dados_cache = cache.obter(codigo, param_inicio, param_fim)
    if dados_cache is not None:
        return dados_cache

    url = BASE_URL.format(codigo=codigo)
    params = {
        "formato": "json",
        "dataInicial": param_inicio,
        "dataFinal": param_fim,
    }
    dados = await _fetch_com_retry(client, url, params, codigo)

    # Salvar no cache
    cache.salvar(codigo, param_inicio, param_fim, dados)

    return dados


async def _buscar_serie_ultimos(
    client: httpx.AsyncClient,
    codigo: int,
    n: int,
) -> List[Dict[str, str]]:
    """Busca os últimos N valores de uma série."""
    url = ULTIMOS_URL.format(codigo=codigo, n=n)
    params = {"formato": "json"}
    return await _fetch_com_retry(client, url, params, codigo)


async def _buscar_serie_completa(
    codigo: int,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    last: Optional[int] = None,
) -> pd.DataFrame:
    """Busca uma série completa com paginação automática se necessário.

    Se o intervalo for superior a 10 anos, divide em chunks e faz
    requisições paralelas (máximo 5 simultâneas).
    """
    async with httpx.AsyncClient() as client:
        # Caso: últimos N valores
        if last is not None:
            dados = await _buscar_serie_ultimos(client, codigo, last)
            return _dados_para_dataframe(dados, codigo)

        # Definir período padrão
        if fim is None:
            fim = date.today()
        if inicio is None:
            inicio = date(fim.year - 10 + 1, fim.month, fim.day)

        # Validação
        if inicio > fim:
            raise ParametrosInvalidos(
                f"Data inicial ({inicio}) não pode ser posterior à data final ({fim})."
            )

        # Gerar intervalos de no máximo 10 anos
        intervalos = _gerar_intervalos(inicio, fim)

        if len(intervalos) == 1:
            dados = await _buscar_serie_periodo(client, codigo, inicio, fim)
            return _dados_para_dataframe(dados, codigo)

        # Múltiplos intervalos: requisições paralelas com semáforo
        semaforo = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def fetch_com_semaforo(ini: date, fi: date) -> List[Dict[str, str]]:
            async with semaforo:
                return await _buscar_serie_periodo(client, codigo, ini, fi)

        tarefas = [fetch_com_semaforo(ini, fi) for ini, fi in intervalos]
        resultados = await asyncio.gather(*tarefas)

        # Concatenar e deduplicar
        todos_dados: List[Dict[str, str]] = []
        for resultado in resultados:
            todos_dados.extend(resultado)

        return _dados_para_dataframe(todos_dados, codigo)


def _dados_para_dataframe(dados: List[Dict[str, str]], codigo: int) -> pd.DataFrame:
    """Converte lista de dicts da API BACEN para DataFrame formatado.

    A API retorna: [{"data": "dd/mm/yyyy", "valor": "1.23"}, ...]
    """
    if not dados:
        logger.warning("Série %d retornou dados vazios.", codigo)
        return pd.DataFrame(columns=["data", "valor"])

    df = pd.DataFrame(dados)

    # Converter data para datetime
    df["data"] = pd.to_datetime(df["data"], format=BACEN_DATE_FORMAT, dayfirst=True)

    # Converter valor para float
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    # Remover duplicatas e ordenar
    df = df.drop_duplicates(subset=["data"]).sort_values("data").reset_index(drop=True)

    # Definir data como índice
    df = df.set_index("data")

    return df


async def _buscar_multiplas_series(
    series: Dict[str, int],
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    last: Optional[int] = None,
) -> pd.DataFrame:
    """Busca múltiplas séries e retorna DataFrame com uma coluna por série.

    Args:
        series: Dict mapeando nome → código (ex: {"Selic": 11, "IPCA": 433})
        inicio: Data inicial (opcional)
        fim: Data final (opcional)
        last: Últimos N valores (opcional, sobrepõe inicio/fim)
    """
    fim_parsed = _parse_date(fim) if isinstance(fim, str) else fim
    inicio_parsed = _parse_date(inicio) if isinstance(inicio, str) else inicio

    if fim_parsed is None and last is None:
        fim_parsed = date.today()
    if inicio_parsed is None and last is None:
        fim_parsed = fim_parsed or date.today()
        inicio_parsed = date(fim_parsed.year - 10 + 1, fim_parsed.month, fim_parsed.day)

    # Buscar cada série
    semaforo = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch_serie(nome: str, codigo: int) -> Tuple[str, pd.DataFrame]:
        async with semaforo:
            df = await _buscar_serie_completa(
                codigo, inicio=inicio_parsed, fim=fim_parsed, last=last
            )
            return nome, df

    tarefas = [fetch_serie(nome, codigo) for nome, codigo in series.items()]
    resultados = await asyncio.gather(*tarefas)

    # Combinar em um único DataFrame
    dfs: Dict[str, pd.Series] = {}
    for nome, df in resultados:
        if not df.empty:
            dfs[nome] = df["valor"]

    if not dfs:
        return pd.DataFrame()

    resultado = pd.DataFrame(dfs)
    resultado.index.name = "data"
    return resultado.sort_index()


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Executa coroutine de forma compatível com ambientes sync e async.

    Trata o caso de já existir um event loop rodando (ex: Jupyter notebooks).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Dentro de um event loop existente (Jupyter, etc.)
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)


def get(
    codigo: Union[int, str, Dict[str, int]],
    start: Union[str, date, datetime, None] = None,
    end: Union[str, date, datetime, None] = None,
    last: Optional[int] = None,
) -> pd.DataFrame:
    """Busca séries temporais da API SGS do Banco Central do Brasil.

    Trata automaticamente a limitação de 10 anos por consulta,
    dividindo em múltiplas requisições quando necessário.

    Args:
        codigo: Código da série SGS (int), nome do catálogo (str),
            ou dict mapeando nomes para códigos.
            Ex: 11, "selic", ou {"Selic": 11, "IPCA": 433}
        start: Data inicial. Aceita 'YYYY-MM-DD', 'DD/MM/YYYY', date ou datetime.
            Se omitido, usa 10 anos antes da data final.
        end: Data final. Aceita os mesmos formatos de start.
            Se omitido, usa a data de hoje.
        last: Buscar os últimos N valores (ignora start/end).

    Returns:
        pandas.DataFrame com índice datetime e coluna 'valor' (série única)
        ou múltiplas colunas nomeadas (múltiplas séries).

    Raises:
        SerieNaoEncontrada: Se o código da série não existe na API.
        BacenAPIError: Se a API retornar erro.
        BacenTimeoutError: Se todas as tentativas de retry falharem.
        ParametrosInvalidos: Se os parâmetros forem inválidos.

    Examples:
        >>> from bacendata import sgs
        >>> # Série única (por código)
        >>> selic = sgs.get(11, start="2020-01-01")
        >>> # Série única (por nome do catálogo)
        >>> selic = sgs.get("selic", start="2020-01-01")
        >>> # Múltiplas séries
        >>> df = sgs.get({"Selic": 11, "IPCA": 433}, start="2010-01-01")
        >>> # Últimos 12 valores
        >>> ipca = sgs.get(433, last=12)
    """
    if isinstance(codigo, dict):
        return _run_async(_buscar_multiplas_series(codigo, inicio=start, fim=end, last=last))

    codigo_int = catalogo.resolver_codigo(codigo)
    inicio = _parse_date(start)
    fim = _parse_date(end)
    return _run_async(_buscar_serie_completa(codigo_int, inicio=inicio, fim=fim, last=last))


async def aget(
    codigo: Union[int, str, Dict[str, int]],
    start: Union[str, date, datetime, None] = None,
    end: Union[str, date, datetime, None] = None,
    last: Optional[int] = None,
) -> pd.DataFrame:
    """Versão async de get(). Mesma interface, para uso em código assíncrono.

    Útil quando já se está dentro de um contexto async (FastAPI, etc).

    Args:
        codigo: Código da série SGS (int), nome do catálogo (str),
            ou dict mapeando nomes para códigos.
        start: Data inicial.
        end: Data final.
        last: Buscar os últimos N valores.

    Returns:
        pandas.DataFrame com séries temporais.
    """
    if isinstance(codigo, dict):
        return await _buscar_multiplas_series(codigo, inicio=start, fim=end, last=last)

    codigo_int = catalogo.resolver_codigo(codigo)
    inicio = _parse_date(start)
    fim = _parse_date(end)
    return await _buscar_serie_completa(codigo_int, inicio=inicio, fim=fim, last=last)


def metadata(codigo: int) -> Dict[str, Union[str, int, None]]:
    """Busca metadados de uma série SGS.

    Args:
        codigo: Código da série SGS.

    Returns:
        Dict com informações da série (nome, periodicidade, fonte, etc).

    Raises:
        SerieNaoEncontrada: Se o código da série não existe.
    """
    return _run_async(ametadata(codigo))


async def ametadata(codigo: int) -> Dict[str, Union[str, int, None]]:
    """Versão async de metadata(). Para uso em contextos assíncronos (FastAPI, etc)."""
    metadata_url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"

    async with httpx.AsyncClient() as client:
        # A API SGS não tem endpoint dedicado de metadados no formato JSON.
        # Fazemos uma requisição com último valor para validar a série,
        # e depois buscamos os metadados via endpoint XML/HTML.
        ultimos_url = ULTIMOS_URL.format(codigo=codigo, n=1)
        params = {"formato": "json"}

        try:
            response = await client.get(ultimos_url, params=params, timeout=DEFAULT_TIMEOUT)
        except httpx.TimeoutException:
            raise BacenTimeoutError(codigo, 1)

        if response.status_code == 404:
            raise SerieNaoEncontrada(codigo)

        if response.status_code >= 400:
            raise BacenAPIError(response.status_code, response.text)

        # Buscar metadados via endpoint principal (retorna HTML/XML)
        try:
            meta_response = await client.get(
                metadata_url,
                params={"formato": "json"},
                timeout=DEFAULT_TIMEOUT,
            )
            if meta_response.status_code == 200:
                try:
                    meta_data = meta_response.json()
                    return {
                        "codigo": codigo,
                        "nome": meta_data.get("nomeCompleto") or meta_data.get("nome"),
                        "unidade": (
                            meta_data.get("unidadePadrao", {}).get("nome")
                            if isinstance(meta_data.get("unidadePadrao"), dict)
                            else meta_data.get("unidadePadrao")
                        ),
                        "periodicidade": (
                            meta_data.get("periodicidade", {}).get("nome")
                            if isinstance(meta_data.get("periodicidade"), dict)
                            else meta_data.get("periodicidade")
                        ),
                        "fonte": (
                            meta_data.get("gestorProprietario", {}).get("nome")
                            if isinstance(meta_data.get("gestorProprietario"), dict)
                            else meta_data.get("gestorProprietario")
                        ),
                        "inicio": meta_data.get("dataInicio"),
                        "fim": meta_data.get("dataFim"),
                    }
                except Exception:
                    pass
        except Exception:
            pass

        # Fallback: retornar dados mínimos
        return {
            "codigo": codigo,
            "nome": None,
            "unidade": None,
            "periodicidade": None,
            "fonte": None,
            "inicio": None,
            "fim": None,
        }
