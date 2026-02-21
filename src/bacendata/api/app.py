"""
bacendata.api.app
~~~~~~~~~~~~~~~~~~

Factory da aplicação FastAPI.

Uso:
    uvicorn bacendata.api.app:create_app --factory --reload --port 8000
"""

import logging

from fastapi import FastAPI

from bacendata.api.middleware.rate_limit import RateLimitMiddleware
from bacendata.api.routes import health, series, webhook
from bacendata.core.config import settings
from bacendata.wrapper import cache

logger = logging.getLogger("bacendata")


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""

    # Sentry: rastreamento de erros em produção
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.2,
            send_default_pii=False,
        )

    app = FastAPI(
        title=settings.app_name,
        description=(
            "API REST para acesso simplificado aos dados do Banco Central do Brasil (SGS).\n\n"
            "**Funcionalidades:**\n"
            "- Consulta de séries temporais por código ou nome\n"
            "- Paginação automática para consultas >10 anos\n"
            "- Catálogo de 14 séries populares com aliases\n"
            "- Consulta bulk de múltiplas séries\n"
            "- Rate limiting por API key\n\n"
            "**Planos:**\n"
            f"- Free: {settings.rate_limit_free} req/dia\n"
            f"- Pro: {settings.rate_limit_pro} req/dia\n"
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    app.add_middleware(RateLimitMiddleware)

    # Rotas
    app.include_router(health.router)
    app.include_router(series.router)
    app.include_router(webhook.router)

    # Ativar cache do wrapper se configurado
    if settings.cache_ativo:
        cache.ativar()
        logger.info("Cache local ativado para a API.")

    return app
