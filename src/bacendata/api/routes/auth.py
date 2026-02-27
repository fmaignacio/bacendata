"""
bacendata.api.routes.auth
~~~~~~~~~~~~~~~~~~~~~~~~~~

Autenticação por API key.

Busca chaves no PostgreSQL. Fallback para variável de ambiente BACENDATA_API_KEYS
quando o banco de dados não está configurado.
"""

import logging
from typing import Dict, Optional, Tuple

from fastapi import Header, HTTPException

from bacendata.core.config import settings

logger = logging.getLogger("bacendata")

# Planos disponíveis e seus limites diários
PLANOS = {
    "free": settings.rate_limit_free,
    "pro": settings.rate_limit_pro,
}


def _carregar_api_keys_env() -> Dict[str, str]:
    """Carrega API keys da variável de ambiente (fallback).

    Formato: "chave1:plano,chave2:plano"
    """
    if not settings.api_keys:
        return {}

    keys = {}
    for item in settings.api_keys.split(","):
        item = item.strip()
        if ":" in item:
            chave, plano = item.split(":", 1)
            keys[chave.strip()] = plano.strip()
    return keys


async def _buscar_key_db(api_key: str) -> Optional[str]:
    """Busca API key no banco de dados. Retorna o plano ou None."""
    from sqlalchemy import select

    from bacendata.core.database import get_session
    from bacendata.core.models import ApiKey

    async with get_session() as session:
        result = await session.execute(
            select(ApiKey.plano).where(ApiKey.key == api_key, ApiKey.ativo.is_(True))
        )
        row = result.scalar_one_or_none()
        return row


async def autenticar_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Tuple[Optional[str], str]:
    """Valida API key e retorna (chave, plano).

    Busca primeiro no banco de dados, depois na variável de ambiente.
    Se nenhuma API key for configurada, permite acesso livre como 'free'.

    Returns:
        Tupla (api_key, plano). api_key pode ser None para acesso anônimo.
    """
    # Se nenhuma key foi enviada
    if not x_api_key:
        return (None, "free")

    # Tentar banco de dados primeiro (se inicializado)
    from bacendata.core import database as db

    db_ativo = db.async_session is not None
    if db_ativo:
        plano = await _buscar_key_db(x_api_key)
        if plano:
            return (x_api_key, plano)

    # Fallback: variável de ambiente
    api_keys_env = _carregar_api_keys_env()
    if api_keys_env:
        plano = api_keys_env.get(x_api_key)
        if plano:
            return (x_api_key, plano)

    # Se não há nenhuma fonte de keys configurada, acesso livre
    if not db_ativo and not api_keys_env:
        return (None, "free")

    # Key inválida
    raise HTTPException(
        status_code=401,
        detail="API key inválida. Verifique sua chave de acesso.",
    )
