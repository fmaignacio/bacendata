"""
bacendata.api.routes.health
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoint de health check.
"""

from fastapi import APIRouter

from bacendata.core.config import settings
from bacendata.schemas.series import HealthResponse

router = APIRouter(tags=["Health"])


@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Verifica se a API está funcionando."""
    return HealthResponse(
        status="ok",
        versao=settings.app_version,
        servico=settings.app_name,
    )
