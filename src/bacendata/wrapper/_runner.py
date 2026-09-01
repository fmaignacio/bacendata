"""
bacendata.wrapper._runner
~~~~~~~~~~~~~~~~~~~~~~~~~

Helper compartilhado para executar coroutines a partir de código síncrono.
"""

import asyncio
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_async(coro: "Coroutine[Any, Any, T]") -> T:
    """Executa coroutine de forma compatível com ambientes sync e async.

    Trata o caso de já existir um event loop rodando (ex: Jupyter notebooks).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Dentro de um event loop existente (Jupyter, etc.)
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)
