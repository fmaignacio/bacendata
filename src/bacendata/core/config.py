"""
bacendata.core.config
~~~~~~~~~~~~~~~~~~~~~

Configuração centralizada da API usando pydantic-settings.

Variáveis de ambiente podem ser definidas em arquivo .env ou diretamente no sistema.
"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da API BacenData."""

    # Aplicação
    app_name: str = "BacenData API"
    app_version: str = "0.2.0"
    debug: bool = False

    # Rate limiting (requisições por dia)
    rate_limit_free: int = 100
    rate_limit_pro: int = 10_000

    # API Keys para demonstração (em produção, usar banco de dados)
    # Formato: "chave1:plano,chave2:plano" ex: "abc123:free,xyz789:pro"
    api_keys: Optional[str] = None

    # BACEN
    bacen_max_concurrent: int = 5
    bacen_timeout: int = 30

    # Cache
    cache_ativo: bool = True

    model_config = {"env_prefix": "BACENDATA_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
