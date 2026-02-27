"""
bacendata.core.models
~~~~~~~~~~~~~~~~~~~~~

Modelos SQLAlchemy para persistência de dados.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    """Tabela de API keys geradas via Stripe webhook."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(52), unique=True, index=True)
    plano: Mapped[str] = mapped_column(String(20), default="pro")
    email: Mapped[str | None] = mapped_column(String(255))
    stripe_session_id: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
