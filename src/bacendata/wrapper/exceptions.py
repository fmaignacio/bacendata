"""
bacendata.wrapper.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exceções customizadas para o wrapper da API SGS do BACEN.
"""


class BacenDataError(Exception):
    """Erro base para todas as exceções do BacenData."""


class SerieNaoEncontrada(BacenDataError):
    """Série temporal não encontrada na API do BACEN.

    Pode indicar código inválido ou série descontinuada.
    """

    def __init__(self, codigo: int) -> None:
        self.codigo = codigo
        super().__init__(f"Série {codigo} não encontrada na API do BACEN.")


class BacenAPIError(BacenDataError):
    """Erro retornado pela API do BACEN.

    Contém o código HTTP e a mensagem de erro original.
    """

    def __init__(self, status_code: int, mensagem: str) -> None:
        self.status_code = status_code
        self.mensagem = mensagem
        super().__init__(f"Erro {status_code} da API BACEN: {mensagem}")


class BacenTimeoutError(BacenDataError):
    """Timeout ao consultar a API do BACEN após todas as tentativas de retry."""

    def __init__(self, codigo: int, tentativas: int) -> None:
        self.codigo = codigo
        self.tentativas = tentativas
        super().__init__(f"Timeout ao consultar série {codigo} após {tentativas} tentativas.")


class ParametrosInvalidos(BacenDataError):
    """Parâmetros de consulta inválidos.

    Ex: data_inicio após data_fim, código negativo, etc.
    """
