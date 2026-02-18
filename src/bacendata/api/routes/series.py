"""
bacendata.api.routes.series
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoints da API para consulta de séries temporais do BACEN SGS.
"""

import logging
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query

from bacendata.api.routes.auth import autenticar_api_key
from bacendata.schemas.series import (
    BulkRequest,
    BulkResponse,
    BulkSerieResponse,
    CatalogoResponse,
    ErrorResponse,
    SerieCatalogo,
    SerieMetadata,
    SerieResponse,
    SerieValor,
)
from bacendata.wrapper import bacen_sgs as sgs
from bacendata.wrapper.catalogo import CATALOGO, buscar_por_nome, listar
from bacendata.wrapper.exceptions import (
    BacenAPIError,
    BacenDataError,
    BacenTimeoutError,
    ParametrosInvalidos,
    SerieNaoEncontrada,
)

logger = logging.getLogger("bacendata")

router = APIRouter(prefix="/api/v1", tags=["Séries Temporais"])


def _df_para_valores(df) -> list[SerieValor]:  # type: ignore[type-arg]
    """Converte DataFrame para lista de SerieValor."""
    valores = []
    for idx, row in df.iterrows():
        data_str = idx.strftime("%d/%m/%Y") if hasattr(idx, "strftime") else str(idx)
        valores.append(SerieValor(data=data_str, valor=float(row["valor"])))
    return valores


def _info_catalogo(codigo: int) -> dict:
    """Retorna info do catálogo para um código, ou campos vazios."""
    serie = CATALOGO.get(codigo)
    if serie:
        return {
            "nome": serie.nome,
            "periodicidade": serie.periodicidade,
            "unidade": serie.unidade,
        }
    return {"nome": None, "periodicidade": None, "unidade": None}


@router.get(
    "/series/{codigo}",
    response_model=SerieResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    summary="Consultar série temporal",
    description="Busca dados de uma série SGS do BACEN por código numérico ou nome do catálogo.",
)
async def get_serie(
    codigo: Union[int, str],
    start: Optional[str] = Query(
        None, description="Data inicial (YYYY-MM-DD ou DD/MM/YYYY)", alias="start"
    ),
    end: Optional[str] = Query(
        None, description="Data final (YYYY-MM-DD ou DD/MM/YYYY)", alias="end"
    ),
    last: Optional[int] = Query(None, gt=0, description="Últimos N valores"),
    auth: tuple = Depends(autenticar_api_key),
) -> SerieResponse:
    """Consulta uma série temporal do BACEN."""
    try:
        # Resolver nome para código se necessário
        codigo_int = _resolver_codigo(codigo)

        df = await sgs.aget(codigo_int, start=start, end=end, last=last)
        valores = _df_para_valores(df)
        info = _info_catalogo(codigo_int)

        return SerieResponse(
            codigo=codigo_int,
            nome=info["nome"],
            periodicidade=info["periodicidade"],
            unidade=info["unidade"],
            dados=valores,
            total=len(valores),
        )
    except SerieNaoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ParametrosInvalidos as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BacenTimeoutError as e:
        raise HTTPException(
            status_code=502,
            detail=f"API do BACEN não respondeu: {e}",
        )
    except BacenAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro na API do BACEN (HTTP {e.status_code}): {e.mensagem}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/series/{codigo}/metadata",
    response_model=SerieMetadata,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    summary="Metadados de uma série",
    description="Retorna metadados de uma série SGS (nome, periodicidade, fonte, etc).",
)
async def get_serie_metadata(
    codigo: int,
    auth: tuple = Depends(autenticar_api_key),
) -> SerieMetadata:
    """Busca metadados de uma série SGS."""
    try:
        meta = await sgs.ametadata(codigo)
        return SerieMetadata(**meta)
    except SerieNaoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BacenDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/series/bulk",
    response_model=BulkResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    summary="Consultar múltiplas séries",
    description="Busca várias séries de uma vez. Máximo 20 séries por requisição.",
)
async def get_series_bulk(
    body: BulkRequest,
    auth: tuple = Depends(autenticar_api_key),
) -> BulkResponse:
    """Consulta múltiplas séries em uma requisição."""
    resultados = []

    for item in body.series:
        try:
            codigo_int = _resolver_codigo(item.codigo)
            df = await sgs.aget(codigo_int, start=body.start, end=body.end, last=body.last)
            valores = _df_para_valores(df)
            info = _info_catalogo(codigo_int)

            resultados.append(
                BulkSerieResponse(
                    codigo=codigo_int,
                    nome=item.nome or info["nome"],
                    dados=valores,
                    total=len(valores),
                )
            )
        except BacenDataError as e:
            logger.warning("Erro ao buscar série %s no bulk: %s", item.codigo, e)
            resultados.append(
                BulkSerieResponse(
                    codigo=codigo_int if isinstance(item.codigo, int) else 0,
                    nome=item.nome or str(item.codigo),
                    dados=[],
                    total=0,
                )
            )

    return BulkResponse(series=resultados, total_series=len(resultados))


@router.get(
    "/catalogo",
    response_model=CatalogoResponse,
    summary="Listar catálogo de séries",
    description="Lista todas as séries disponíveis no catálogo com aliases.",
)
async def get_catalogo(
    auth: tuple = Depends(autenticar_api_key),
) -> CatalogoResponse:
    """Lista todas as séries do catálogo."""
    series = listar()
    items = [
        SerieCatalogo(
            codigo=s.codigo,
            nome=s.nome,
            descricao=s.descricao,
            periodicidade=s.periodicidade,
            unidade=s.unidade,
            aliases=s.aliases,
        )
        for s in series
    ]
    return CatalogoResponse(series=items, total=len(items))


@router.get(
    "/catalogo/search",
    response_model=CatalogoResponse,
    summary="Buscar série no catálogo",
    description="Busca séries por nome ou alias no catálogo.",
)
async def search_catalogo(
    q: str = Query(..., min_length=1, description="Termo de busca"),
    auth: tuple = Depends(autenticar_api_key),
) -> CatalogoResponse:
    """Busca séries no catálogo por nome ou alias."""
    q_lower = q.lower()
    resultados = []

    for serie in listar():
        # Buscar no nome, descrição e aliases
        if (
            q_lower in serie.nome.lower()
            or q_lower in serie.descricao.lower()
            or any(q_lower in alias.lower() for alias in serie.aliases)
        ):
            resultados.append(
                SerieCatalogo(
                    codigo=serie.codigo,
                    nome=serie.nome,
                    descricao=serie.descricao,
                    periodicidade=serie.periodicidade,
                    unidade=serie.unidade,
                    aliases=serie.aliases,
                )
            )

    return CatalogoResponse(series=resultados, total=len(resultados))


def _resolver_codigo(codigo: Union[int, str]) -> int:
    """Resolve código int ou nome str para código numérico."""
    if isinstance(codigo, int):
        return codigo
    if isinstance(codigo, str):
        # Tentar converter string numérica
        try:
            return int(codigo)
        except ValueError:
            pass
        # Buscar no catálogo
        serie = buscar_por_nome(codigo)
        if serie:
            return serie.codigo
        raise ValueError(
            f"Série '{codigo}' não encontrada no catálogo. "
            f"Use GET /api/v1/catalogo para ver séries disponíveis."
        )
    raise ValueError(f"Código deve ser int ou str, recebeu {type(codigo).__name__}.")
