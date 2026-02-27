"""
bacendata.api.routes.dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoints do dashboard do usuário.

Permite que clientes autenticados vejam seu plano, uso e estatísticas.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from bacendata.api.routes.auth import autenticar_api_key

logger = logging.getLogger("bacendata")

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


@router.get(
    "/me",
    summary="Informações do usuário",
    description="Retorna informações da API key autenticada: plano, data de criação, uso hoje.",
)
async def get_me(auth: tuple = Depends(autenticar_api_key)):
    """Retorna informações do usuário autenticado."""
    api_key, plano = auth

    if not api_key:
        return {
            "autenticado": False,
            "plano": "free",
            "mensagem": "Acesso anônimo. Use uma API key para ver seu dashboard.",
        }

    # Buscar dados no banco
    from bacendata.core import database as db

    if db.async_session is None:
        return {
            "autenticado": True,
            "plano": plano,
            "api_key_preview": f"{api_key[:8]}...{api_key[-4:]}",
        }

    from bacendata.core.config import settings
    from bacendata.core.database import get_session
    from bacendata.core.models import ApiKey, UsageLog

    async with get_session() as session:
        # Info da API key
        result = await session.execute(
            select(ApiKey).where(ApiKey.key == api_key, ApiKey.ativo.is_(True))
        )
        key_info = result.scalar_one_or_none()

        if not key_info:
            raise HTTPException(status_code=401, detail="API key não encontrada.")

        # Uso hoje
        inicio_dia = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(func.count(UsageLog.id)).where(
                UsageLog.api_key == api_key,
                UsageLog.criado_em >= inicio_dia,
            )
        )
        uso_hoje = result.scalar() or 0

        limite = (
            settings.rate_limit_pro if plano in ("pro", "enterprise") else settings.rate_limit_free
        )

        return {
            "autenticado": True,
            "plano": key_info.plano,
            "email": key_info.email,
            "api_key_preview": f"{api_key[:8]}...{api_key[-4:]}",
            "criado_em": key_info.criado_em.isoformat() if key_info.criado_em else None,
            "ativo": key_info.ativo,
            "uso": {
                "hoje": uso_hoje,
                "limite_diario": limite,
                "restante": max(0, limite - uso_hoje),
            },
        }


@router.get(
    "/usage",
    summary="Estatísticas de uso",
    description="Retorna estatísticas detalhadas de uso da API nos últimos 30 dias.",
)
async def get_usage(auth: tuple = Depends(autenticar_api_key)):
    """Retorna estatísticas de uso detalhadas."""
    api_key, plano = auth

    if not api_key:
        return {
            "autenticado": False,
            "mensagem": "Envie sua API key via header X-API-Key para ver estatísticas.",
        }

    from bacendata.core import database as db

    if db.async_session is None:
        return {"autenticado": True, "plano": plano, "estatisticas": None}

    from bacendata.core.database import get_session
    from bacendata.core.models import UsageLog

    agora = datetime.now(timezone.utc)
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_7d = agora - timedelta(days=7)
    inicio_30d = agora - timedelta(days=30)

    async with get_session() as session:
        # Uso hoje
        result = await session.execute(
            select(func.count(UsageLog.id)).where(
                UsageLog.api_key == api_key,
                UsageLog.criado_em >= inicio_dia,
            )
        )
        uso_hoje = result.scalar() or 0

        # Uso 7 dias
        result = await session.execute(
            select(func.count(UsageLog.id)).where(
                UsageLog.api_key == api_key,
                UsageLog.criado_em >= inicio_7d,
            )
        )
        uso_7d = result.scalar() or 0

        # Uso 30 dias
        result = await session.execute(
            select(func.count(UsageLog.id)).where(
                UsageLog.api_key == api_key,
                UsageLog.criado_em >= inicio_30d,
            )
        )
        uso_30d = result.scalar() or 0

        # Endpoints mais usados (top 5)
        result = await session.execute(
            select(UsageLog.endpoint, func.count(UsageLog.id).label("total"))
            .where(
                UsageLog.api_key == api_key,
                UsageLog.criado_em >= inicio_30d,
            )
            .group_by(UsageLog.endpoint)
            .order_by(func.count(UsageLog.id).desc())
            .limit(5)
        )
        top_endpoints = [{"endpoint": row[0], "total": row[1]} for row in result.all()]

        # Uso diário dos últimos 7 dias
        result = await session.execute(
            select(
                func.date(UsageLog.criado_em).label("dia"),
                func.count(UsageLog.id).label("total"),
            )
            .where(
                UsageLog.api_key == api_key,
                UsageLog.criado_em >= inicio_7d,
            )
            .group_by(func.date(UsageLog.criado_em))
            .order_by(func.date(UsageLog.criado_em))
        )
        uso_diario = [{"dia": str(row[0]), "total": row[1]} for row in result.all()]

        return {
            "autenticado": True,
            "plano": plano,
            "uso": {
                "hoje": uso_hoje,
                "ultimos_7_dias": uso_7d,
                "ultimos_30_dias": uso_30d,
            },
            "top_endpoints": top_endpoints,
            "uso_diario": uso_diario,
        }
