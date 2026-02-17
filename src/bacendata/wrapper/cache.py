"""
bacendata.wrapper.cache
~~~~~~~~~~~~~~~~~~~~~~~~

Cache local em SQLite para evitar chamadas repetidas à API do BACEN.

O cache armazena séries já consultadas e respeita um TTL configurável
por periodicidade da série:
    - Séries diárias: 1 hora
    - Séries semanais: 6 horas
    - Séries mensais: 24 horas

Uso:
    >>> from bacendata import sgs
    >>> sgs.cache.ativar()  # Ativa cache em ~/.bacendata/cache.db
    >>> selic = sgs.get(11, start="2020-01-01")  # Primeira vez: busca na API
    >>> selic = sgs.get(11, start="2020-01-01")  # Segunda vez: lê do cache
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("bacendata")

# TTL padrão por periodicidade (em segundos)
TTL_PADRAO: Dict[str, int] = {
    "diária": 3600,  # 1 hora
    "semanal": 21600,  # 6 horas
    "mensal": 86400,  # 24 horas
}
TTL_DEFAULT = 3600  # 1 hora para séries sem periodicidade conhecida

_CACHE_DIR = Path.home() / ".bacendata"
_CACHE_DB = _CACHE_DIR / "cache.db"

# Estado global do cache
_ativo = False
_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    """Retorna conexão com o banco SQLite, criando tabela se necessário."""
    global _conn
    if _conn is not None:
        return _conn

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(_CACHE_DB))
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_series (
            chave TEXT PRIMARY KEY,
            dados TEXT NOT NULL,
            timestamp REAL NOT NULL,
            ttl INTEGER NOT NULL
        )
        """)
    _conn.commit()
    return _conn


def ativar(caminho: Optional[str] = None) -> None:
    """Ativa o cache local SQLite.

    Args:
        caminho: Caminho customizado para o arquivo .db.
            Se omitido, usa ~/.bacendata/cache.db
    """
    global _ativo, _conn, _CACHE_DB

    if caminho:
        _CACHE_DB = Path(caminho)

    _conn = None  # Força reconexão no próximo acesso
    _ativo = True
    logger.info("Cache local ativado em %s", _CACHE_DB)


def desativar() -> None:
    """Desativa o cache local."""
    global _ativo, _conn
    if _conn is not None:
        _conn.close()
        _conn = None
    _ativo = False
    logger.info("Cache local desativado.")


def esta_ativo() -> bool:
    """Retorna True se o cache está ativo."""
    return _ativo


def _gerar_chave(codigo: int, param_inicio: str, param_fim: str) -> str:
    """Gera chave única para uma consulta."""
    return f"{codigo}:{param_inicio}:{param_fim}"


def obter(
    codigo: int, param_inicio: str, param_fim: str, ttl: Optional[int] = None
) -> Optional[List[Dict[str, str]]]:
    """Busca dados no cache.

    Args:
        codigo: Código da série SGS.
        param_inicio: Data inicial formatada (DD/MM/YYYY).
        param_fim: Data final formatada (DD/MM/YYYY).
        ttl: TTL customizado em segundos. Se omitido, usa TTL_DEFAULT.

    Returns:
        Lista de dicts com dados da série, ou None se cache miss/expirado.
    """
    if not _ativo:
        return None

    chave = _gerar_chave(codigo, param_inicio, param_fim)
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT dados, timestamp, ttl FROM cache_series WHERE chave = ?",
        (chave,),
    )
    row = cursor.fetchone()

    if row is None:
        return None

    dados_json, timestamp, ttl_salvo = row
    ttl_efetivo = ttl if ttl is not None else ttl_salvo
    idade = time.time() - timestamp

    if idade > ttl_efetivo:
        # Cache expirado
        conn.execute("DELETE FROM cache_series WHERE chave = ?", (chave,))
        conn.commit()
        return None

    logger.debug("Cache hit para série %d (%s a %s)", codigo, param_inicio, param_fim)
    return json.loads(dados_json)


def salvar(
    codigo: int,
    param_inicio: str,
    param_fim: str,
    dados: List[Dict[str, str]],
    ttl: Optional[int] = None,
) -> None:
    """Salva dados no cache.

    Args:
        codigo: Código da série SGS.
        param_inicio: Data inicial formatada (DD/MM/YYYY).
        param_fim: Data final formatada (DD/MM/YYYY).
        dados: Lista de dicts com dados da série.
        ttl: TTL em segundos. Se omitido, usa TTL_DEFAULT.
    """
    if not _ativo:
        return

    chave = _gerar_chave(codigo, param_inicio, param_fim)
    ttl_efetivo = ttl if ttl is not None else TTL_DEFAULT
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO cache_series (chave, dados, timestamp, ttl)
        VALUES (?, ?, ?, ?)
        """,
        (chave, json.dumps(dados), time.time(), ttl_efetivo),
    )
    conn.commit()
    logger.debug("Cache salvo para série %d (%s a %s)", codigo, param_inicio, param_fim)


def limpar() -> None:
    """Remove todos os dados do cache."""
    if not _ativo:
        return
    conn = _get_conn()
    conn.execute("DELETE FROM cache_series")
    conn.commit()
    logger.info("Cache limpo.")


def limpar_expirados() -> int:
    """Remove apenas entradas expiradas do cache.

    Returns:
        Número de entradas removidas.
    """
    if not _ativo:
        return 0
    conn = _get_conn()
    agora = time.time()
    cursor = conn.execute(
        "DELETE FROM cache_series WHERE (? - timestamp) > ttl",
        (agora,),
    )
    conn.commit()
    removidos = cursor.rowcount
    if removidos:
        logger.info("Cache: %d entradas expiradas removidas.", removidos)
    return removidos
