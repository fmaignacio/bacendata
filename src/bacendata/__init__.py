"""
BacenData — Acesso simplificado aos dados do Banco Central do Brasil.

Uso rápido:
    >>> from bacendata import sgs
    >>> selic = sgs.get(11, start="2020-01-01")
"""

from bacendata.wrapper import bacen_sgs as sgs

__version__ = "0.1.0"
__all__ = ["sgs", "__version__"]
