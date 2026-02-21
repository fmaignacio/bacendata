"""
bacendata.api.routes.webhook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Webhook do Stripe para processar pagamentos e gerar API keys.

Fluxo:
1. Cliente paga via Payment Link do Stripe
2. Stripe envia evento checkout.session.completed
3. Webhook gera API key e salva no arquivo de keys
4. Key é enviada ao cliente via metadata do Stripe
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from bacendata.core.config import settings

logger = logging.getLogger("bacendata")

router = APIRouter(tags=["Webhook"])

# Arquivo onde as API keys são persistidas
KEYS_FILE = Path("/app/data/api_keys.json")

# Mapeamento de Price ID → plano
PRICE_TO_PLAN = {
    "price_1T3I5I2cO5c0PQGeanIeAVvA": "pro",
    "price_1T3I6q2cO5c0PQGeUqQMXM1y": "enterprise",
}


def _gerar_api_key() -> str:
    """Gera uma API key segura com prefixo identificador."""
    token = secrets.token_hex(24)
    return f"bcd_{token}"


def _carregar_keys() -> dict:
    """Carrega API keys do arquivo JSON."""
    if KEYS_FILE.exists():
        return json.loads(KEYS_FILE.read_text())
    return {}


def _salvar_keys(keys: dict) -> None:
    """Salva API keys no arquivo JSON."""
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEYS_FILE.write_text(json.dumps(keys, indent=2))


def _verificar_assinatura(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verifica assinatura do webhook Stripe (v1)."""
    try:
        elements = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = elements.get("t", "")
        signature = elements.get("v1", "")

        signed_payload = f"{timestamp}.{payload.decode()}"
        expected = hmac.new(
            secret.encode(), signed_payload.encode(), hashlib.sha256
        ).hexdigest()

        # Verificar tolerância de tempo (5 minutos)
        if abs(time.time() - int(timestamp)) > 300:
            return False

        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Recebe eventos do Stripe e gera API keys para novos assinantes."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verificar assinatura se o secret estiver configurado
    if settings.stripe_webhook_secret:
        if not _verificar_assinatura(payload, sig_header, settings.stripe_webhook_secret):
            raise HTTPException(status_code=400, detail="Assinatura inválida")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido")

    # Processar apenas checkout concluído
    if event.get("type") != "checkout.session.completed":
        return {"status": "ignored", "type": event.get("type")}

    session = event["data"]["object"]
    customer_email = session.get("customer_email") or session.get("customer_details", {}).get(
        "email"
    )

    # Determinar plano a partir dos line items
    plano = "pro"  # default
    line_items = session.get("line_items", {}).get("data", [])
    for item in line_items:
        price_id = item.get("price", {}).get("id", "")
        if price_id in PRICE_TO_PLAN:
            plano = PRICE_TO_PLAN[price_id]
            break

    # Tentar via metadata do Payment Link
    if "metadata" in session:
        plano = session["metadata"].get("plan", plano)

    # Gerar API key
    api_key = _gerar_api_key()

    # Salvar no arquivo de keys
    keys = _carregar_keys()
    keys[api_key] = {
        "plano": plano,
        "email": customer_email,
        "stripe_session_id": session.get("id"),
        "criado_em": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _salvar_keys(keys)

    # Atualizar variável de ambiente em memória para o rate limiter reconhecer
    existing = settings.api_keys or ""
    new_entry = f"{api_key}:{plano}"
    settings.api_keys = f"{existing},{new_entry}" if existing else new_entry

    logger.info(
        "Nova API key gerada: plano=%s email=%s key=%s...%s",
        plano,
        customer_email,
        api_key[:8],
        api_key[-4:],
    )

    return {
        "status": "ok",
        "api_key": api_key,
        "plano": plano,
        "email": customer_email,
    }
