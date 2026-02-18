"""
bacendata.schemas.series
~~~~~~~~~~~~~~~~~~~~~~~~~

Schemas Pydantic para request/response da API de séries temporais.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, Field

# ============================================================================
# Response schemas
# ============================================================================


class SerieValor(BaseModel):
    """Um ponto de dados de uma série temporal."""

    data: str = Field(..., description="Data no formato DD/MM/YYYY")
    valor: float = Field(..., description="Valor numérico da série")


class SerieResponse(BaseModel):
    """Resposta para consulta de série única."""

    codigo: int = Field(..., description="Código SGS da série")
    nome: Optional[str] = Field(None, description="Nome da série (se disponível no catálogo)")
    periodicidade: Optional[str] = Field(None, description="Periodicidade da série")
    unidade: Optional[str] = Field(None, description="Unidade de medida")
    dados: List[SerieValor] = Field(..., description="Lista de valores da série")
    total: int = Field(..., description="Total de registros retornados")


class SerieCatalogo(BaseModel):
    """Informações de uma série do catálogo."""

    codigo: int
    nome: str
    descricao: str
    periodicidade: str
    unidade: str
    aliases: List[str]


class CatalogoResponse(BaseModel):
    """Resposta para listagem do catálogo."""

    series: List[SerieCatalogo]
    total: int


class SerieMetadata(BaseModel):
    """Metadados de uma série SGS."""

    codigo: int
    nome: Optional[str] = None
    unidade: Optional[str] = None
    periodicidade: Optional[str] = None
    fonte: Optional[str] = None
    inicio: Optional[str] = None
    fim: Optional[str] = None


class HealthResponse(BaseModel):
    """Resposta do health check."""

    status: str = "ok"
    versao: str
    servico: str = "BacenData API"


class ErrorResponse(BaseModel):
    """Resposta de erro padrão."""

    detail: str


# ============================================================================
# Request schemas
# ============================================================================


class BulkSerieItem(BaseModel):
    """Item de uma consulta bulk."""

    codigo: Union[int, str] = Field(..., description="Código SGS ou nome do catálogo")
    nome: Optional[str] = Field(None, description="Rótulo opcional para a série")


class BulkRequest(BaseModel):
    """Requisição para consulta de múltiplas séries."""

    series: List[BulkSerieItem] = Field(
        ..., min_length=1, max_length=20, description="Lista de séries para consultar"
    )
    start: Optional[str] = Field(None, description="Data inicial (YYYY-MM-DD ou DD/MM/YYYY)")
    end: Optional[str] = Field(None, description="Data final (YYYY-MM-DD ou DD/MM/YYYY)")
    last: Optional[int] = Field(None, gt=0, description="Últimos N valores")


class BulkSerieResponse(BaseModel):
    """Resposta de uma série dentro do bulk."""

    codigo: int
    nome: Optional[str] = None
    dados: List[SerieValor]
    total: int


class BulkResponse(BaseModel):
    """Resposta da consulta bulk."""

    series: List[BulkSerieResponse]
    total_series: int
