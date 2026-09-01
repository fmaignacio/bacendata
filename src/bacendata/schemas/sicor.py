"""
bacendata.schemas.sicor
~~~~~~~~~~~~~~~~~~~~~~~

Schemas Pydantic para request/response da API SICOR (crédito rural).
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class SicorRecurso(BaseModel):
    """Um recurso disponível na API SICOR."""

    nome: str = Field(..., description="Nome do recurso OData")
    descricao: str = Field(..., description="Descrição do recurso")


class SicorRecursosResponse(BaseModel):
    """Resposta para listagem de recursos do SICOR."""

    recursos: List[SicorRecurso] = Field(..., description="Recursos conhecidos")
    total: int = Field(..., description="Total de recursos")


class SicorResponse(BaseModel):
    """Resposta para consulta de um recurso do SICOR.

    As colunas de cada registro são definidas pela própria API do BACEN,
    por isso os registros são dicionários livres.
    """

    recurso: str = Field(..., description="Nome do recurso consultado")
    colunas: List[str] = Field(..., description="Nomes das colunas retornadas")
    dados: List[Dict[str, Any]] = Field(..., description="Registros retornados")
    total: int = Field(..., description="Total de registros retornados")
    skip: int = Field(..., description="Registros pulados no início")


class SicorColunasResponse(BaseModel):
    """Resposta para inspeção do schema de um recurso."""

    recurso: str = Field(..., description="Nome do recurso consultado")
    colunas: List[str] = Field(..., description="Nomes das colunas do recurso")
    total: int = Field(..., description="Total de colunas")
