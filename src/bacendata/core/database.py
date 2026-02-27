"""
bacendata.core.database
~~~~~~~~~~~~~~~~~~~~~~~

Configuração do banco de dados async com SQLAlchemy.

Em produção usa PostgreSQL (asyncpg).
Em testes usa SQLite (aiosqlite).
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bacendata.core.models import Base

logger = logging.getLogger("bacendata")

# Engine e session factory globais (inicializados em init_db)
engine = None
async_session: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str) -> None:
    """Inicializa o engine e cria as tabelas se não existirem."""
    global engine, async_session

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_info = database_url.split("@")[-1] if "@" in database_url else "local"
    logger.info("Banco de dados inicializado: %s", db_info)


async def close_db() -> None:
    """Fecha o engine do banco de dados."""
    global engine, async_session
    if engine:
        await engine.dispose()
        engine = None
        async_session = None
        logger.info("Conexão com banco de dados encerrada.")


def get_session() -> AsyncSession:
    """Retorna uma nova sessão async. Deve ser usada com 'async with'."""
    if async_session is None:
        raise RuntimeError("Banco de dados não inicializado. Chame init_db() primeiro.")
    return async_session()
