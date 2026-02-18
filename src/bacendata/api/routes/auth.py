"""
bacendata.api.routes.auth
~~~~~~~~~~~~~~~~~~~~~~~~~~

Autenticação por API key.

No MVP, as chaves são configuradas via variável de ambiente BACENDATA_API_KEYS.
Em produção, serão armazenadas no PostgreSQL.
"""

import logging
from typing import Optional, Tuple

from fastapi import Header, HTTPException

from bacendata.core.config import settings

logger = logging.getLogger("bacendata")

# Planos disponíveis e seus limites diários
PLANOS = {
    "free": settings.rate_limit_free,
    "pro": settings.rate_limit_pro,
}


def _carregar_api_keys() -> dict[str, str]:
    """Carrega API keys da configuração.

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


def autenticar_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Tuple[Optional[str], str]:
    """Valida API key e retorna (chave, plano).

    Se nenhuma API key for configurada no servidor, permite acesso livre como 'free'.
    Se API keys estiverem configuradas e a chave for inválida, retorna 401.

    Returns:
        Tupla (api_key, plano). api_key pode ser None para acesso anônimo.
    """
    api_keys = _carregar_api_keys()

    # Se nenhuma key está configurada, acesso livre
    if not api_keys:
        return (None, "free")

    # Se keys estão configuradas mas nenhuma foi enviada
    if not x_api_key:
        return (None, "free")

    # Validar a key enviada
    plano = api_keys.get(x_api_key)
    if plano is None:
        raise HTTPException(
            status_code=401,
            detail="API key inválida. Verifique sua chave de acesso.",
        )

    return (x_api_key, plano)
