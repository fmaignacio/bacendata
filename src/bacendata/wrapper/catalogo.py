"""
bacendata.wrapper.catalogo
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Catálogo de séries populares do SGS/BACEN.

Permite buscar séries pelo nome em vez do código numérico:
    >>> from bacendata import sgs
    >>> selic = sgs.get("selic")
"""

from typing import Dict, List, Optional


class Serie:
    """Metadados de uma série do catálogo."""

    def __init__(
        self,
        codigo: int,
        nome: str,
        descricao: str,
        periodicidade: str,
        unidade: str,
        aliases: Optional[List[str]] = None,
    ) -> None:
        self.codigo = codigo
        self.nome = nome
        self.descricao = descricao
        self.periodicidade = periodicidade
        self.unidade = unidade
        self.aliases = aliases or []

    def __repr__(self) -> str:
        return f"Serie({self.codigo}, '{self.nome}', {self.periodicidade})"


# Séries prioritárias definidas no CLAUDE.md
CATALOGO: Dict[int, Serie] = {
    11: Serie(
        codigo=11,
        nome="Selic diária",
        descricao="Taxa de juros Selic diária",
        periodicidade="diária",
        unidade="% a.a.",
        aliases=["selic", "selic_diaria"],
    ),
    12: Serie(
        codigo=12,
        nome="Selic acumulada no mês",
        descricao="Taxa Selic acumulada no mês",
        periodicidade="mensal",
        unidade="% a.m.",
        aliases=["selic_mensal", "selic_acumulada"],
    ),
    433: Serie(
        codigo=433,
        nome="IPCA",
        descricao="IPCA - Variação mensal",
        periodicidade="mensal",
        unidade="% a.m.",
        aliases=["ipca", "inflacao"],
    ),
    4390: Serie(
        codigo=4390,
        nome="Selic acumulada anualizada",
        descricao="Taxa Selic acumulada no mês anualizada",
        periodicidade="mensal",
        unidade="% a.a.",
        aliases=["selic_anual", "selic_anualizada"],
    ),
    1: Serie(
        codigo=1,
        nome="Dólar (compra)",
        descricao="Taxa de câmbio - Dólar americano (compra) - PTAX",
        periodicidade="diária",
        unidade="R$/US$",
        aliases=["dolar", "usd", "ptax", "cambio"],
    ),
    10813: Serie(
        codigo=10813,
        nome="Euro (compra)",
        descricao="Taxa de câmbio - Euro (compra)",
        periodicidade="diária",
        unidade="R$/EUR",
        aliases=["euro", "eur"],
    ),
    4189: Serie(
        codigo=4189,
        nome="Juros PF",
        descricao="Taxa média de juros - Pessoa Física",
        periodicidade="mensal",
        unidade="% a.a.",
        aliases=["juros_pf", "taxa_pf"],
    ),
    25434: Serie(
        codigo=25434,
        nome="Juros Crédito Livre",
        descricao="Taxa média de juros - Crédito Livre Total",
        periodicidade="mensal",
        unidade="% a.a.",
        aliases=["juros_credito", "credito_livre"],
    ),
    20542: Serie(
        codigo=20542,
        nome="Saldo Crédito Livre",
        descricao="Saldo da carteira de crédito com recursos livres - Total",
        periodicidade="mensal",
        unidade="R$ milhões",
        aliases=["saldo_credito", "carteira_credito"],
    ),
    21112: Serie(
        codigo=21112,
        nome="Inadimplência PF",
        descricao="Inadimplência da carteira de crédito - Pessoa Física",
        periodicidade="mensal",
        unidade="%",
        aliases=["inadimplencia_pf", "default_pf"],
    ),
    21082: Serie(
        codigo=21082,
        nome="Inadimplência PJ",
        descricao="Inadimplência da carteira de crédito - Pessoa Jurídica",
        periodicidade="mensal",
        unidade="%",
        aliases=["inadimplencia_pj", "default_pj"],
    ),
    7326: Serie(
        codigo=7326,
        nome="Reservas Internacionais",
        descricao="Reservas internacionais - Conceito liquidez",
        periodicidade="diária",
        unidade="US$ milhões",
        aliases=["reservas", "reservas_internacionais"],
    ),
    27574: Serie(
        codigo=27574,
        nome="Expectativa IPCA 12m",
        descricao="Expectativa mediana do IPCA para os próximos 12 meses (Focus)",
        periodicidade="semanal",
        unidade="% a.a.",
        aliases=["focus_ipca", "expectativa_ipca"],
    ),
    27575: Serie(
        codigo=27575,
        nome="Expectativa Selic",
        descricao="Expectativa mediana da taxa Selic (Focus)",
        periodicidade="semanal",
        unidade="% a.a.",
        aliases=["focus_selic", "expectativa_selic"],
    ),
}

# Índice reverso: alias → código
_ALIAS_MAP: Dict[str, int] = {}
for _codigo, _serie in CATALOGO.items():
    for _alias in _serie.aliases:
        _ALIAS_MAP[_alias.lower()] = _codigo
    _ALIAS_MAP[_serie.nome.lower()] = _codigo


def buscar_por_nome(nome: str) -> Optional[Serie]:
    """Busca uma série pelo nome ou alias.

    Args:
        nome: Nome ou alias da série (case-insensitive).

    Returns:
        Objeto Serie se encontrado, None caso contrário.

    Examples:
        >>> buscar_por_nome("selic")
        Serie(11, 'Selic diária', diária)
        >>> buscar_por_nome("ipca")
        Serie(433, 'IPCA', mensal)
    """
    codigo = _ALIAS_MAP.get(nome.lower())
    if codigo is not None:
        return CATALOGO[codigo]
    return None


def listar() -> List[Serie]:
    """Lista todas as séries disponíveis no catálogo.

    Returns:
        Lista de objetos Serie ordenada por código.
    """
    return sorted(CATALOGO.values(), key=lambda s: s.codigo)


def resolver_codigo(codigo_ou_nome: object) -> int:
    """Resolve um código numérico ou nome/alias para código SGS.

    Args:
        codigo_ou_nome: Código int ou nome/alias string.

    Returns:
        Código numérico da série SGS.

    Raises:
        ValueError: Se o nome não for encontrado no catálogo.
    """
    if isinstance(codigo_ou_nome, int):
        return codigo_ou_nome
    if isinstance(codigo_ou_nome, str):
        serie = buscar_por_nome(codigo_ou_nome)
        if serie is not None:
            return serie.codigo
        raise ValueError(
            f"Série '{codigo_ou_nome}' não encontrada no catálogo. "
            f"Use sgs.catalogo.listar() para ver as séries disponíveis."
        )
    raise TypeError(f"Código deve ser int ou str, recebeu {type(codigo_ou_nome).__name__}.")
