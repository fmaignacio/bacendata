"""
BacenData — Acesso simplificado aos dados do Banco Central do Brasil.

Uso rápido:
    >>> from bacendata import sgs
    >>> selic = sgs.get(11, start="2020-01-01")

    >>> from bacendata import sicor
    >>> df = sicor.get("CusteioMunicipioProduto", limit=1000)
"""

from bacendata.wrapper import bacen_sgs as sgs
from bacendata.wrapper import sicor

__version__ = "0.2.0"
__all__ = ["sgs", "sicor", "__version__"]
