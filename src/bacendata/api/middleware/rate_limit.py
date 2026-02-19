"""
bacendata.api.middleware.rate_limit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Middleware de rate limiting simples em memória.

No MVP, usa um dicionário em memória. Em produção, usar Redis.
"""

import logging
import time
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from bacendata.core.config import settings

logger = logging.getLogger("bacendata")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting por IP com janela diária.

    Limites:
        - Sem API key (free): BACENDATA_RATE_LIMIT_FREE req/dia (padrão 100)
        - Com API key pro: BACENDATA_RATE_LIMIT_PRO req/dia (padrão 10.000)
    """

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        # {identificador: (contagem, timestamp_inicio_janela)}
        self._contadores: Dict[str, Tuple[int, float]] = {}
        self._janela = 86400  # 24 horas em segundos

    def _identificador(self, request: Request) -> str:
        """Retorna identificador único para rate limiting."""
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"
        # Fallback para IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _limite_para_request(self, request: Request) -> int:
        """Retorna o limite de requisições baseado na API key."""
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return settings.rate_limit_pro
        return settings.rate_limit_free

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        # Não limitar health check e docs
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        identificador = self._identificador(request)
        limite = self._limite_para_request(request)
        agora = time.time()

        contagem, inicio = self._contadores.get(identificador, (0, agora))

        # Resetar janela se expirou
        if agora - inicio >= self._janela:
            contagem = 0
            inicio = agora

        contagem += 1
        self._contadores[identificador] = (contagem, inicio)

        if contagem > limite:
            tempo_restante = int(self._janela - (agora - inicio))
            logger.warning(
                "Rate limit excedido para %s (%d/%d)",
                identificador,
                contagem,
                limite,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "erro": "Limite de requisições excedido.",
                    "detalhe": f"Limite: {limite} req/dia. "
                    f"Tente novamente em {tempo_restante}s. "
                    f"Para mais requisições, use uma API key Pro.",
                },
                headers={"Retry-After": str(tempo_restante)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limite)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limite - contagem))
        return response
