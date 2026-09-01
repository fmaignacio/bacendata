"""
bacendata.api.routes.sicor
~~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoints da API para consulta de dados do SICOR (crédito rural).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from bacendata.api.routes.auth import autenticar_api_key
from bacendata.schemas.series import ErrorResponse
from bacendata.schemas.sicor import (
    SicorColunasResponse,
    SicorRecurso,
    SicorRecursosResponse,
    SicorResponse,
)
from bacendata.wrapper import sicor
from bacendata.wrapper.exceptions import (
    BacenAPIError,
    ParametrosInvalidos,
    RecursoNaoEncontrado,
    SicorTimeoutError,
)

logger = logging.getLogger("bacendata")

router = APIRouter(prefix="/api/v1/sicor", tags=["SICOR — Crédito Rural"])

# Teto de registros por requisição HTTP, para não estourar a resposta JSON.
MAX_LIMIT = 50000


@router.get(
    "/recursos",
    response_model=SicorRecursosResponse,
    summary="Listar recursos do SICOR",
    description="Lista os recursos conhecidos da Matriz de Dados do Crédito Rural.",
)
async def get_recursos(
    auth: tuple = Depends(autenticar_api_key),
) -> SicorRecursosResponse:
    """Lista os recursos conhecidos do SICOR."""
    recursos = [
        SicorRecurso(nome=nome, descricao=descricao)
        for nome, descricao in sicor.listar_recursos().items()
    ]
    return SicorRecursosResponse(recursos=recursos, total=len(recursos))


@router.get(
    "/{recurso}/colunas",
    response_model=SicorColunasResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    summary="Inspecionar colunas de um recurso",
    description="Retorna os nomes das colunas de um recurso do SICOR.",
)
async def get_colunas(
    recurso: str,
    auth: tuple = Depends(autenticar_api_key),
) -> SicorColunasResponse:
    """Descobre o schema de um recurso do SICOR."""
    try:
        cols = await sicor.acolunas(recurso)
        return SicorColunasResponse(recurso=recurso, colunas=cols, total=len(cols))
    except RecursoNaoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SicorTimeoutError as e:
        raise HTTPException(status_code=502, detail=f"API do BACEN não respondeu: {e}")
    except BacenAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro na API do BACEN (HTTP {e.status_code}): {e.mensagem}",
        )


@router.get(
    "/{recurso}",
    response_model=SicorResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    summary="Consultar recurso do SICOR",
    description=(
        "Consulta um recurso da Matriz de Dados do Crédito Rural. "
        "Suporta filtro, seleção de colunas e ordenação no padrão OData."
    ),
)
async def get_recurso(
    recurso: str,
    filtro: Optional[str] = Query(
        None, description="Expressão OData $filter (ex: AnoEmissao eq 2023)"
    ),
    select: Optional[str] = Query(
        None, description="Colunas separadas por vírgula (OData $select)"
    ),
    orderby: Optional[str] = Query(None, description="Ordenação (OData $orderby)"),
    limit: int = Query(
        1000, gt=0, le=MAX_LIMIT, description=f"Máximo de registros (até {MAX_LIMIT})"
    ),
    skip: int = Query(0, ge=0, description="Registros a pular no início"),
    auth: tuple = Depends(autenticar_api_key),
) -> SicorResponse:
    """Consulta um recurso do SICOR com paginação automática."""
    try:
        df = await sicor.aget(
            recurso,
            filtro=filtro,
            select=select,
            orderby=orderby,
            limit=limit,
            skip=skip,
        )
        registros = df.to_dict(orient="records")
        return SicorResponse(
            recurso=recurso,
            colunas=list(df.columns),
            dados=registros,
            total=len(registros),
            skip=skip,
        )
    except RecursoNaoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ParametrosInvalidos as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SicorTimeoutError as e:
        raise HTTPException(status_code=502, detail=f"API do BACEN não respondeu: {e}")
    except BacenAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro na API do BACEN (HTTP {e.status_code}): {e.mensagem}",
        )
