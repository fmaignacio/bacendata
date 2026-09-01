"""
Testes unitários para o wrapper SICOR.

Utiliza respx para mockar chamadas HTTP à API Olinda do BACEN.
"""

import httpx
import pandas as pd
import pytest
import respx

from bacendata.wrapper import sicor
from bacendata.wrapper.exceptions import (
    BacenAPIError,
    ParametrosInvalidos,
    RecursoNaoEncontrado,
    SicorTimeoutError,
)

RECURSO = "CusteioMunicipioProduto"
URL = f"{sicor.BASE_URL}/{RECURSO}"


def _envelope(registros: list[dict]) -> dict:
    """Monta o envelope OData retornado pelo Olinda."""
    return {
        "@odata.context": f"{sicor.BASE_URL}/$metadata#{RECURSO}",
        "value": registros,
    }


def _registros(n: int, offset: int = 0) -> list[dict]:
    """Gera N registros mockados com um schema arbitrário."""
    return [
        {"AnoEmissao": 2023, "cdMunicipio": 1000 + i + offset, "VlCusteio": 100.5 + i}
        for i in range(n)
    ]


# ============================================================================
# Consulta básica
# ============================================================================


class TestGetBasico:
    @respx.mock
    def test_retorna_dataframe(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(3))))

        df = sicor.get(RECURSO, limit=3)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    @respx.mock
    def test_colunas_vem_da_api(self) -> None:
        """O wrapper não impõe schema: usa as colunas retornadas pela API."""
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(2))))

        df = sicor.get(RECURSO, limit=2)

        assert list(df.columns) == ["AnoEmissao", "cdMunicipio", "VlCusteio"]

    @respx.mock
    def test_schema_desconhecido_passa_direto(self) -> None:
        """Campos novos publicados pelo BACEN aparecem sem alteração no código."""
        registros = [{"CampoNovoQualquer": "x", "Outro": 1}]
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(registros)))

        df = sicor.get(RECURSO, limit=1)

        assert list(df.columns) == ["CampoNovoQualquer", "Outro"]
        assert df.iloc[0]["CampoNovoQualquer"] == "x"

    @respx.mock
    def test_recurso_vazio_retorna_dataframe_vazio(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope([])))

        df = sicor.get(RECURSO)

        assert df.empty

    @respx.mock
    def test_resposta_sem_campo_value(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(200, json={"@odata.context": "x"}))

        df = sicor.get(RECURSO)

        assert df.empty


# ============================================================================
# Parâmetros OData
# ============================================================================


class TestParametrosOData:
    @respx.mock
    def test_formato_json_sempre_enviado(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, limit=1)

        assert rota.calls[0].request.url.params["$format"] == "json"

    @respx.mock
    def test_filtro_enviado(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, filtro="AnoEmissao eq 2023", limit=1)

        assert rota.calls[0].request.url.params["$filter"] == "AnoEmissao eq 2023"

    @respx.mock
    def test_select_como_lista(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, select=["AnoEmissao", "VlCusteio"], limit=1)

        assert rota.calls[0].request.url.params["$select"] == "AnoEmissao,VlCusteio"

    @respx.mock
    def test_select_como_string(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, select="AnoEmissao", limit=1)

        assert rota.calls[0].request.url.params["$select"] == "AnoEmissao"

    @respx.mock
    def test_orderby_enviado(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, orderby="AnoEmissao desc", limit=1)

        assert rota.calls[0].request.url.params["$orderby"] == "AnoEmissao desc"

    @respx.mock
    def test_skip_inicial_enviado(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, limit=1, skip=500)

        assert rota.calls[0].request.url.params["$skip"] == "500"

    @respx.mock
    def test_params_extras_para_recurso_parametrizado(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        sicor.get(RECURSO, limit=1, params={"@AnoInicio": "2023"})

        assert rota.calls[0].request.url.params["@AnoInicio"] == "2023"


# ============================================================================
# Paginação automática
# ============================================================================


class TestPaginacao:
    @respx.mock
    def test_pagina_ate_esgotar_recurso(self) -> None:
        """Página cheia seguida de página parcial encerra a busca."""
        respx.get(URL).mock(
            side_effect=[
                httpx.Response(200, json=_envelope(_registros(3))),
                httpx.Response(200, json=_envelope(_registros(3, offset=3))),
                httpx.Response(200, json=_envelope(_registros(1, offset=6))),
            ]
        )

        df = sicor.get(RECURSO, page_size=3)

        assert len(df) == 7

    @respx.mock
    def test_para_quando_pagina_vem_vazia(self) -> None:
        respx.get(URL).mock(
            side_effect=[
                httpx.Response(200, json=_envelope(_registros(2))),
                httpx.Response(200, json=_envelope([])),
            ]
        )

        df = sicor.get(RECURSO, page_size=2)

        assert len(df) == 2

    @respx.mock
    def test_skip_avanca_entre_paginas(self) -> None:
        rota = respx.get(URL).mock(
            side_effect=[
                httpx.Response(200, json=_envelope(_registros(2))),
                httpx.Response(200, json=_envelope(_registros(1, offset=2))),
            ]
        )

        sicor.get(RECURSO, page_size=2)

        assert rota.calls[0].request.url.params["$skip"] == "0"
        assert rota.calls[1].request.url.params["$skip"] == "2"

    @respx.mock
    def test_limit_interrompe_paginacao(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(5))))

        df = sicor.get(RECURSO, limit=5, page_size=5)

        assert len(df) == 5
        assert len(rota.calls) == 1

    @respx.mock
    def test_limit_menor_que_page_size_reduz_top(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(2))))

        sicor.get(RECURSO, limit=2, page_size=1000)

        assert rota.calls[0].request.url.params["$top"] == "2"

    @respx.mock
    def test_limit_nao_ultrapassado_com_multiplas_paginas(self) -> None:
        respx.get(URL).mock(
            side_effect=[
                httpx.Response(200, json=_envelope(_registros(2))),
                httpx.Response(200, json=_envelope(_registros(2, offset=2))),
            ]
        )

        df = sicor.get(RECURSO, limit=3, page_size=2)

        assert len(df) == 3


# ============================================================================
# Validação de parâmetros
# ============================================================================


class TestValidacao:
    def test_limit_zero(self) -> None:
        with pytest.raises(ParametrosInvalidos):
            sicor.get(RECURSO, limit=0)

    def test_limit_negativo(self) -> None:
        with pytest.raises(ParametrosInvalidos):
            sicor.get(RECURSO, limit=-5)

    def test_skip_negativo(self) -> None:
        with pytest.raises(ParametrosInvalidos):
            sicor.get(RECURSO, skip=-1)

    def test_page_size_zero(self) -> None:
        with pytest.raises(ParametrosInvalidos):
            sicor.get(RECURSO, page_size=0)


# ============================================================================
# Erros e retry
# ============================================================================


class TestErros:
    @respx.mock
    def test_404_levanta_recurso_nao_encontrado(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(404))

        with pytest.raises(RecursoNaoEncontrado):
            sicor.get(RECURSO, limit=1)

    @respx.mock
    def test_400_levanta_bacen_api_error(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(400, text="filtro inválido"))

        with pytest.raises(BacenAPIError):
            sicor.get(RECURSO, limit=1)

    @respx.mock
    def test_retry_apos_500(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _sem_espera(_segundos: float) -> None:
            return None

        monkeypatch.setattr(sicor, "_dormir", _sem_espera)

        rota = respx.get(URL).mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(200, json=_envelope(_registros(1))),
            ]
        )

        df = sicor.get(RECURSO, limit=1)

        assert len(df) == 1
        assert len(rota.calls) == 2

    @respx.mock
    def test_timeout_apos_todas_tentativas(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def _sem_espera(_segundos: float) -> None:
            return None

        monkeypatch.setattr(sicor, "_dormir", _sem_espera)

        respx.get(URL).mock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(SicorTimeoutError):
            sicor.get(RECURSO, limit=1)


# ============================================================================
# Catálogo de recursos e inspeção de schema
# ============================================================================


class TestRecursos:
    def test_listar_recursos_nao_vazio(self) -> None:
        recursos = sicor.listar_recursos()

        assert recursos
        assert "CusteioMunicipioProduto" in recursos

    def test_listar_recursos_retorna_copia(self) -> None:
        """Mutar o retorno não deve afetar o catálogo do módulo."""
        recursos = sicor.listar_recursos()
        recursos["Inventado"] = "x"

        assert "Inventado" not in sicor.listar_recursos()

    @respx.mock
    def test_colunas_inspeciona_um_registro(self) -> None:
        rota = respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        cols = sicor.colunas(RECURSO)

        assert cols == ["AnoEmissao", "cdMunicipio", "VlCusteio"]
        assert rota.calls[0].request.url.params["$top"] == "1"

    @respx.mock
    def test_colunas_recurso_vazio(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope([])))

        assert sicor.colunas(RECURSO) == []


# ============================================================================
# Interface async
# ============================================================================


class TestAsync:
    @respx.mock
    @pytest.mark.asyncio
    async def test_aget(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(2))))

        df = await sicor.aget(RECURSO, limit=2)

        assert len(df) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_acolunas(self) -> None:
        respx.get(URL).mock(return_value=httpx.Response(200, json=_envelope(_registros(1))))

        cols = await sicor.acolunas(RECURSO)

        assert cols == ["AnoEmissao", "cdMunicipio", "VlCusteio"]
