"""
bacendata.wrapper.sicor
~~~~~~~~~~~~~~~~~~~~~~~

Cliente para a API SICOR (Sistema de Operações do Crédito Rural e do Proagro)
do Banco Central do Brasil, publicada na plataforma Olinda.

Diferente do SGS, o SICOR não é uma série temporal: é um conjunto de recursos
OData tabulares (a Matriz de Dados do Crédito Rural — MDCR). Por isso a
paginação aqui é por *registros* (``$top``/``$skip``), e não por intervalo de
datas. O wrapper trata a paginação automaticamente, buscando todas as páginas
até esgotar o recurso.

Os nomes das colunas retornadas são definidos pela própria API e repassados
sem alteração para o DataFrame — o wrapper não impõe um schema fixo, de forma
que novos campos publicados pelo BACEN aparecem automaticamente.

Uso:
    >>> from bacendata import sicor
    >>> df = sicor.get("CusteioMunicipioProduto", limit=1000)
    >>> df = sicor.get("CusteioMunicipioProduto", filtro="AnoEmissao eq 2023")
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx
import pandas as pd

from bacendata.wrapper._runner import run_async
from bacendata.wrapper.exceptions import (
    BacenAPIError,
    ParametrosInvalidos,
    RecursoNaoEncontrado,
    SicorTimeoutError,
)

logger = logging.getLogger("bacendata")

# Constantes
BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/odata"
PAGE_SIZE = 10000  # registros por requisição
DEFAULT_TIMEOUT = 60  # segundos (payloads do SICOR são maiores que os do SGS)
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 5]  # segundos entre retries

# Recursos conhecidos da Matriz de Dados do Crédito Rural (MDCR).
#
# Esta lista é uma conveniência para descoberta, não uma restrição: `get()`
# aceita qualquer nome de recurso publicado pelo BACEN. O catálogo oficial e
# sempre atualizado fica no navegador de dados da plataforma Olinda:
# https://olinda.bcb.gov.br/olinda/servico/SICOR/versao/v2/aplicacao#!/
RECURSOS: Dict[str, str] = {
    "CusteioMunicipioProduto": (
        "Quantidade e valor dos contratos de custeio por município e produto"
    ),
    "CusteioInvestimentoComercialIndustrialSemFiltros": (
        "Contratos de custeio, investimento, comercialização e industrialização por município"
    ),
    "FonteRecursos": "Contratos por fonte de recursos",
    "ProgramaSubprograma": "Contratos por programa e subprograma",
    "RegiaoUFGenero": "Contratos por região, UF e gênero",
    "Faixa": "Contratos por faixa de valores",
}


def listar_recursos() -> Dict[str, str]:
    """Lista os recursos conhecidos do SICOR com suas descrições.

    Returns:
        Dict mapeando nome do recurso → descrição.

    Note:
        `get()` aceita qualquer recurso publicado pelo BACEN, inclusive os que
        não estiverem nesta lista.
    """
    return dict(RECURSOS)


def _montar_query(
    top: int,
    skip: int,
    filtro: Optional[str] = None,
    select: Union[str, Sequence[str], None] = None,
    orderby: Optional[str] = None,
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Monta os parâmetros de query OData para uma página."""
    query: Dict[str, str] = {
        "$format": "json",
        "$top": str(top),
        "$skip": str(skip),
    }
    if filtro:
        query["$filter"] = filtro
    if select:
        query["$select"] = select if isinstance(select, str) else ",".join(select)
    if orderby:
        query["$orderby"] = orderby
    if params:
        # Permite parâmetros extras e recursos parametrizados do Olinda,
        # no formato Recurso(param=@param)?@param='valor'
        query.update(params)
    return query


async def _fetch_pagina(
    client: httpx.AsyncClient,
    recurso: str,
    query: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Busca uma página do recurso com retry e backoff.

    Retorna a lista contida no campo `value` do envelope OData.
    """
    url = f"{BASE_URL}/{recurso}"
    last_exception: Optional[Exception] = None

    for tentativa in range(MAX_RETRIES):
        try:
            response = await client.get(url, params=query, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 404:
                raise RecursoNaoEncontrado(recurso)

            if response.status_code == 400:
                raise BacenAPIError(400, response.text)

            if response.status_code == 429:
                backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
                logger.warning(
                    "Rate limit (429) no recurso %s. Aguardando %ds...", recurso, backoff
                )
                await _dormir(backoff)
                continue

            if response.status_code >= 500:
                backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
                logger.warning(
                    "Erro %d no recurso %s. Retry %d/%d em %ds...",
                    response.status_code,
                    recurso,
                    tentativa + 1,
                    MAX_RETRIES,
                    backoff,
                )
                await _dormir(backoff)
                continue

            response.raise_for_status()

            dados = response.json()
            if not isinstance(dados, dict):
                return []
            valores = dados.get("value")
            if not isinstance(valores, list):
                return []
            return valores

        except httpx.TimeoutException:
            last_exception = SicorTimeoutError(recurso, tentativa + 1)
            backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
            logger.warning(
                "Timeout no recurso %s. Retry %d/%d em %ds...",
                recurso,
                tentativa + 1,
                MAX_RETRIES,
                backoff,
            )
            await _dormir(backoff)
        except (RecursoNaoEncontrado, BacenAPIError, ParametrosInvalidos):
            raise
        except httpx.HTTPStatusError as e:
            last_exception = BacenAPIError(e.response.status_code, str(e))
            backoff = RETRY_BACKOFF[min(tentativa, len(RETRY_BACKOFF) - 1)]
            await _dormir(backoff)

    if last_exception:
        raise last_exception
    raise SicorTimeoutError(recurso, MAX_RETRIES)


async def _dormir(segundos: float) -> None:
    """Wrapper de asyncio.sleep isolado para facilitar testes."""
    import asyncio

    await asyncio.sleep(segundos)


def _validar_parametros(limit: Optional[int], skip: int, page_size: int) -> None:
    """Valida os parâmetros de paginação."""
    if limit is not None and limit <= 0:
        raise ParametrosInvalidos(f"limit deve ser maior que zero, recebeu {limit}.")
    if skip < 0:
        raise ParametrosInvalidos(f"skip não pode ser negativo, recebeu {skip}.")
    if page_size <= 0:
        raise ParametrosInvalidos(f"page_size deve ser maior que zero, recebeu {page_size}.")


async def _buscar_paginado(
    recurso: str,
    filtro: Optional[str] = None,
    select: Union[str, Sequence[str], None] = None,
    orderby: Optional[str] = None,
    limit: Optional[int] = None,
    skip: int = 0,
    page_size: int = PAGE_SIZE,
    params: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Busca todas as páginas de um recurso até esgotar ou atingir `limit`."""
    _validar_parametros(limit, skip, page_size)

    registros: List[Dict[str, Any]] = []
    offset = skip

    async with httpx.AsyncClient() as client:
        while True:
            if limit is not None:
                restante = limit - len(registros)
                if restante <= 0:
                    break
                top = min(page_size, restante)
            else:
                top = page_size

            query = _montar_query(top, offset, filtro, select, orderby, params)
            pagina = await _fetch_pagina(client, recurso, query)

            if not pagina:
                break

            recebidos = len(pagina)

            # A API não deveria devolver mais que `top`, mas truncamos para
            # garantir que `limit` seja sempre respeitado.
            if recebidos > top:
                pagina = pagina[:top]

            registros.extend(pagina)
            offset += len(pagina)

            # Página incompleta significa fim do recurso
            if recebidos < top:
                break

    return registros


def _registros_para_dataframe(registros: List[Dict[str, Any]], recurso: str) -> pd.DataFrame:
    """Converte a lista de registros OData em DataFrame.

    As colunas são exatamente as retornadas pela API, sem renomeação.
    """
    if not registros:
        logger.warning("Recurso %s retornou dados vazios.", recurso)
        return pd.DataFrame()

    return pd.DataFrame(registros)


def get(
    recurso: str,
    filtro: Optional[str] = None,
    select: Union[str, Sequence[str], None] = None,
    orderby: Optional[str] = None,
    limit: Optional[int] = None,
    skip: int = 0,
    page_size: int = PAGE_SIZE,
    params: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Consulta um recurso da API SICOR do Banco Central.

    A paginação é automática: o wrapper busca páginas sucessivas de
    `page_size` registros até esgotar o recurso ou atingir `limit`.

    Args:
        recurso: Nome do recurso OData (ex: "CusteioMunicipioProduto").
            Use `listar_recursos()` para ver os recursos conhecidos.
        filtro: Expressão OData `$filter` (ex: "AnoEmissao eq 2023").
        select: Colunas a retornar, como string ou sequência de nomes.
        orderby: Expressão OData `$orderby` (ex: "AnoEmissao desc").
        limit: Máximo de registros a retornar. Se omitido, busca todos.
        skip: Número de registros a pular no início.
        page_size: Registros por requisição (padrão 10.000).
        params: Parâmetros extras de query. Necessário para recursos
            parametrizados do Olinda, no formato
            ``{"@AnoInicio": "2023"}`` para ``Recurso(AnoInicio=@AnoInicio)``.

    Returns:
        pandas.DataFrame com as colunas retornadas pela API. DataFrame vazio
        se o recurso não retornar registros.

    Raises:
        RecursoNaoEncontrado: Se o recurso não existe na API.
        BacenAPIError: Se a API retornar erro.
        SicorTimeoutError: Se todas as tentativas de retry falharem.
        ParametrosInvalidos: Se os parâmetros de paginação forem inválidos.

    Examples:
        >>> from bacendata import sicor
        >>> # Primeiros 1.000 registros de custeio por município e produto
        >>> df = sicor.get("CusteioMunicipioProduto", limit=1000)
        >>> # Filtrando por ano
        >>> df = sicor.get("CusteioMunicipioProduto", filtro="AnoEmissao eq 2023")
        >>> # Selecionando colunas específicas
        >>> df = sicor.get("FonteRecursos", select=["AnoEmissao", "MesEmissao"])
    """
    registros = run_async(
        _buscar_paginado(
            recurso,
            filtro=filtro,
            select=select,
            orderby=orderby,
            limit=limit,
            skip=skip,
            page_size=page_size,
            params=params,
        )
    )
    return _registros_para_dataframe(registros, recurso)


async def aget(
    recurso: str,
    filtro: Optional[str] = None,
    select: Union[str, Sequence[str], None] = None,
    orderby: Optional[str] = None,
    limit: Optional[int] = None,
    skip: int = 0,
    page_size: int = PAGE_SIZE,
    params: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Versão async de get(). Mesma interface, para uso em código assíncrono.

    Útil quando já se está dentro de um contexto async (FastAPI, etc).
    """
    registros = await _buscar_paginado(
        recurso,
        filtro=filtro,
        select=select,
        orderby=orderby,
        limit=limit,
        skip=skip,
        page_size=page_size,
        params=params,
    )
    return _registros_para_dataframe(registros, recurso)


def colunas(recurso: str) -> List[str]:
    """Retorna os nomes das colunas de um recurso, inspecionando 1 registro.

    Útil para descobrir o schema antes de montar filtros ou selects.

    Args:
        recurso: Nome do recurso OData.

    Returns:
        Lista com os nomes das colunas. Vazia se o recurso não tiver dados.
    """
    return run_async(acolunas(recurso))


async def acolunas(recurso: str) -> List[str]:
    """Versão async de colunas()."""
    registros = await _buscar_paginado(recurso, limit=1, page_size=1)
    if not registros:
        return []
    return list(registros[0].keys())
