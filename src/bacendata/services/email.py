"""
bacendata.services.email
~~~~~~~~~~~~~~~~~~~~~~~~

Envio de email com API key via Resend após pagamento no Stripe.
"""

import logging

import resend

from bacendata.core.config import settings

logger = logging.getLogger("bacendata")


def enviar_api_key(email: str, api_key: str, plano: str) -> bool:
    """Envia a API key por email ao cliente.

    Retorna True se enviou com sucesso, False se falhou ou Resend não configurado.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY não configurada — email não enviado para %s", email)
        return False

    resend.api_key = settings.resend_api_key

    plano_display = plano.capitalize()
    limite = "10.000" if plano == "pro" else "100.000"

    try:
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [email],
                "subject": f"Sua API Key BacenData ({plano_display})",
                "html": _template_email(api_key, plano_display, limite),
            }
        )
        logger.info("Email enviado com sucesso para %s (plano %s)", email, plano)
        return True
    except Exception:
        logger.exception("Falha ao enviar email para %s", email)
        return False


def _template_email(api_key: str, plano: str, limite: str) -> str:
    return f"""\
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #1a1a2e; border-radius: 12px; padding: 32px; color: #ffffff;">
    <h1 style="margin: 0 0 8px; font-size: 24px;">BacenData API</h1>
    <p style="margin: 0 0 24px; color: #a0a0b0; font-size: 14px;">Dados do Banco Central do Brasil</p>

    <div style="background: #16213e; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
      <p style="margin: 0 0 4px; color: #a0a0b0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Sua API Key</p>
      <code style="font-size: 16px; color: #00d4aa; word-break: break-all;">{api_key}</code>
    </div>

    <table style="width: 100%; margin-bottom: 24px;">
      <tr>
        <td style="color: #a0a0b0; font-size: 13px; padding: 4px 0;">Plano</td>
        <td style="color: #ffffff; font-size: 13px; padding: 4px 0; text-align: right;"><strong>{plano}</strong></td>
      </tr>
      <tr>
        <td style="color: #a0a0b0; font-size: 13px; padding: 4px 0;">Limite</td>
        <td style="color: #ffffff; font-size: 13px; padding: 4px 0; text-align: right;"><strong>{limite} req/dia</strong></td>
      </tr>
    </table>

    <div style="background: #16213e; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
      <p style="margin: 0 0 8px; color: #a0a0b0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Exemplo de uso</p>
      <code style="font-size: 13px; color: #e0e0e0; white-space: pre-wrap;">curl -H "X-API-Key: {api_key}" \\
  "https://api.bacendata.com/api/v1/series/433?last=5"</code>
    </div>

    <p style="margin: 0 0 8px; color: #a0a0b0; font-size: 13px;">
      Documentacao completa: <a href="https://api.bacendata.com/docs" style="color: #00d4aa;">api.bacendata.com/docs</a>
    </p>

    <hr style="border: none; border-top: 1px solid #2a2a4e; margin: 24px 0;" />
    <p style="margin: 0; color: #606080; font-size: 11px;">
      Guarde esta chave em local seguro. Ela nao sera exibida novamente.
      Em caso de duvidas, responda este email.
    </p>
  </div>
</div>"""
