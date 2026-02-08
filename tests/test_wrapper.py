"""
Testes unitários para o wrapper bacen_sgs.

Utiliza respx para mockar chamadas HTTP à API do BACEN.
"""

from datetime import date, datetime

import httpx
import pandas as pd
import pytest
import respx

from bacendata.wrapper.bacen_sgs import (
    BASE_URL,
    ULTIMOS_URL,
    _dados_para_dataframe,
    _gerar_intervalos,
    _parse_date,
    get,
    metadata,
)
from bacendata.wrapper.exceptions import (
    BacenAPIError,
    ParametrosInvalidos,
    SerieNaoEncontrada,
)

# ============================================================================
# Fixtures e helpers
# ============================================================================

SELIC_CODIGO = 11
IPCA_CODIGO = 433


def _mock_dados(n: int = 5, inicio_ano: int = 2020) -> list[dict[str, str]]:
    """Gera dados mockados no formato da API BACEN."""
    return [{"data": f"0{i+1}/01/{inicio_ano}", "valor": f"{i + 0.5:.2f}"} for i in range(n)]


# ============================================================================
# Testes de _parse_date
# ============================================================================


class TestParseDate:
    def test_parse_none(self) -> None:
        assert _parse_date(None) is None

    def test_parse_date_object(self) -> None:
        d = date(2024, 1, 15)
        assert _parse_date(d) == d

    def test_parse_datetime_object(self) -> None:
        dt = datetime(2024, 6, 20, 10, 30)
        assert _parse_date(dt) == date(2024, 6, 20)

    def test_parse_iso_string(self) -> None:
        assert _parse_date("2024-03-15") == date(2024, 3, 15)

    def test_parse_br_string(self) -> None:
        assert _parse_date("15/03/2024") == date(2024, 3, 15)

    def test_parse_invalid_string(self) -> None:
        with pytest.raises(ParametrosInvalidos):
            _parse_date("invalid-date")

    def test_parse_empty_string(self) -> None:
        with pytest.raises(ParametrosInvalidos):
            _parse_date("")


# ============================================================================
# Testes de _gerar_intervalos
# ============================================================================


class TestGerarIntervalos:
    def test_intervalo_menor_que_10_anos(self) -> None:
        inicio = date(2020, 1, 1)
        fim = date(2025, 12, 31)
        intervalos = _gerar_intervalos(inicio, fim)
        assert len(intervalos) == 1
        assert intervalos[0] == (inicio, fim)

    def test_intervalo_exato_10_anos(self) -> None:
        inicio = date(2015, 1, 1)
        fim = date(2024, 12, 31)
        intervalos = _gerar_intervalos(inicio, fim)
        assert len(intervalos) == 1

    def test_intervalo_maior_que_10_anos(self) -> None:
        inicio = date(2000, 1, 1)
        fim = date(2024, 12, 31)
        intervalos = _gerar_intervalos(inicio, fim)
        assert len(intervalos) > 1
        # Verificar cobertura completa
        assert intervalos[0][0] == inicio
        assert intervalos[-1][1] == fim
        # Verificar que não há gaps
        for i in range(len(intervalos) - 1):
            diff = (intervalos[i + 1][0] - intervalos[i][1]).days
            assert diff == 1

    def test_intervalo_30_anos(self) -> None:
        inicio = date(1995, 1, 1)
        fim = date(2024, 12, 31)
        intervalos = _gerar_intervalos(inicio, fim)
        assert len(intervalos) == 3


# ============================================================================
# Testes de _dados_para_dataframe
# ============================================================================


class TestDadosParaDataframe:
    def test_dados_vazios(self) -> None:
        df = _dados_para_dataframe([], 11)
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == ["data", "valor"]

    def test_conversao_basica(self) -> None:
        dados = [
            {"data": "01/01/2024", "valor": "11.75"},
            {"data": "02/01/2024", "valor": "11.80"},
        ]
        df = _dados_para_dataframe(dados, 11)
        assert len(df) == 2
        assert df.index.name == "data"
        assert df["valor"].dtype == float
        assert df["valor"].iloc[0] == 11.75

    def test_remove_duplicatas(self) -> None:
        dados = [
            {"data": "01/01/2024", "valor": "11.75"},
            {"data": "01/01/2024", "valor": "11.75"},
            {"data": "02/01/2024", "valor": "11.80"},
        ]
        df = _dados_para_dataframe(dados, 11)
        assert len(df) == 2

    def test_ordena_por_data(self) -> None:
        dados = [
            {"data": "15/03/2024", "valor": "1.0"},
            {"data": "01/01/2024", "valor": "2.0"},
            {"data": "20/02/2024", "valor": "3.0"},
        ]
        df = _dados_para_dataframe(dados, 11)
        datas = df.index.tolist()
        assert datas == sorted(datas)


# ============================================================================
# Testes de get() - série única
# ============================================================================


class TestGetSerieUnica:
    @respx.mock
    def test_get_basico(self) -> None:
        """Busca simples de uma série com período dentro de 10 anos."""
        url = BASE_URL.format(codigo=11)
        dados = [
            {"data": "02/01/2024", "valor": "11.75"},
            {"data": "03/01/2024", "valor": "11.80"},
        ]
        respx.get(url).mock(return_value=httpx.Response(200, json=dados))

        df = get(11, start="2024-01-01", end="2024-12-31")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df["valor"].iloc[0] == 11.75

    @respx.mock
    def test_get_last(self) -> None:
        """Busca os últimos N valores."""
        url = ULTIMOS_URL.format(codigo=433, n=5)
        dados = _mock_dados(5)
        respx.get(url).mock(return_value=httpx.Response(200, json=dados))

        df = get(433, last=5)
        assert len(df) == 5

    @respx.mock
    def test_get_serie_nao_encontrada(self) -> None:
        """Série inexistente deve levantar SerieNaoEncontrada."""
        url = BASE_URL.format(codigo=99999)
        respx.get(url).mock(return_value=httpx.Response(404))

        with pytest.raises(SerieNaoEncontrada) as exc_info:
            get(99999, start="2024-01-01", end="2024-12-31")
        assert exc_info.value.codigo == 99999

    @respx.mock
    def test_get_dados_vazios(self) -> None:
        """Série sem dados retorna DataFrame vazio."""
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(return_value=httpx.Response(200, json=[]))

        df = get(11, start="2024-01-01", end="2024-06-30")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    @respx.mock
    def test_get_erro_400(self) -> None:
        """Erro de parâmetros inválidos na API."""
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(return_value=httpx.Response(400, text="Filtro inválido"))

        with pytest.raises(BacenAPIError) as exc_info:
            get(11, start="2024-01-01", end="2024-12-31")
        assert exc_info.value.status_code == 400

    def test_get_data_inicio_maior_que_fim(self) -> None:
        """Data início > data fim deve levantar ParametrosInvalidos."""
        with pytest.raises(ParametrosInvalidos):
            get(11, start="2025-01-01", end="2020-01-01")


# ============================================================================
# Testes de paginação automática
# ============================================================================


class TestPaginacaoAutomatica:
    @respx.mock
    def test_paginacao_20_anos(self) -> None:
        """Consulta de 20 anos deve gerar 2+ requisições paginadas."""
        url = BASE_URL.format(codigo=11)

        # Mock que retorna dados para qualquer requisição
        dados_chunk = [{"data": "01/06/2010", "valor": "10.0"}]
        respx.get(url).mock(return_value=httpx.Response(200, json=dados_chunk))

        df = get(11, start="2005-01-01", end="2024-12-31")
        assert isinstance(df, pd.DataFrame)
        # Deve ter feito múltiplas chamadas
        assert respx.calls.call_count >= 2

    @respx.mock
    def test_paginacao_sem_duplicatas(self) -> None:
        """Dados nas bordas de chunks não devem gerar duplicatas."""
        url = BASE_URL.format(codigo=11)
        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(
                    200,
                    json=[
                        {"data": "31/12/2014", "valor": "11.0"},
                        {"data": "01/01/2015", "valor": "12.0"},
                    ],
                )
            else:
                return httpx.Response(
                    200,
                    json=[
                        {"data": "01/01/2015", "valor": "12.0"},
                        {"data": "02/01/2015", "valor": "13.0"},
                    ],
                )

        respx.get(url).mock(side_effect=side_effect)

        df = get(11, start="2005-01-01", end="2024-12-31")
        # Data 01/01/2015 deve aparecer apenas uma vez
        datas = df.index.tolist()
        assert len(datas) == len(set(datas))


# ============================================================================
# Testes de retry
# ============================================================================


class TestRetry:
    @respx.mock
    def test_retry_apos_500(self) -> None:
        """Deve fazer retry após erro 500 e retornar dados."""
        url = BASE_URL.format(codigo=11)
        dados = [{"data": "01/01/2024", "valor": "11.75"}]

        route = respx.get(url)
        route.side_effect = [
            httpx.Response(500, text="Internal Server Error"),
            httpx.Response(200, json=dados),
        ]

        df = get(11, start="2024-01-01", end="2024-12-31")
        assert len(df) == 1
        assert respx.calls.call_count == 2

    @respx.mock
    def test_retry_apos_429(self) -> None:
        """Deve fazer retry após rate limit (429)."""
        url = BASE_URL.format(codigo=11)
        dados = [{"data": "01/01/2024", "valor": "11.75"}]

        route = respx.get(url)
        route.side_effect = [
            httpx.Response(429, text="Too Many Requests"),
            httpx.Response(200, json=dados),
        ]

        df = get(11, start="2024-01-01", end="2024-12-31")
        assert len(df) == 1


# ============================================================================
# Testes de múltiplas séries
# ============================================================================


class TestMultiplasSeries:
    @respx.mock
    def test_get_multiplas_series(self) -> None:
        """Busca de múltiplas séries retorna DataFrame com múltiplas colunas."""
        url_selic = BASE_URL.format(codigo=11)
        url_ipca = BASE_URL.format(codigo=433)

        dados_selic = [
            {"data": "01/01/2024", "valor": "11.75"},
            {"data": "01/02/2024", "valor": "11.25"},
        ]
        dados_ipca = [
            {"data": "01/01/2024", "valor": "0.56"},
            {"data": "01/02/2024", "valor": "0.83"},
        ]

        respx.get(url_selic).mock(return_value=httpx.Response(200, json=dados_selic))
        respx.get(url_ipca).mock(return_value=httpx.Response(200, json=dados_ipca))

        df = get(
            {"Selic": 11, "IPCA": 433},
            start="2024-01-01",
            end="2024-12-31",
        )
        assert isinstance(df, pd.DataFrame)
        assert "Selic" in df.columns
        assert "IPCA" in df.columns
        assert df["Selic"].iloc[0] == 11.75
        assert df["IPCA"].iloc[0] == 0.56

    @respx.mock
    def test_get_multiplas_series_com_last(self) -> None:
        """Múltiplas séries com last=N."""
        url_selic = ULTIMOS_URL.format(codigo=11, n=3)
        url_ipca = ULTIMOS_URL.format(codigo=433, n=3)

        dados_selic = _mock_dados(3)
        dados_ipca = _mock_dados(3)

        respx.get(url_selic).mock(return_value=httpx.Response(200, json=dados_selic))
        respx.get(url_ipca).mock(return_value=httpx.Response(200, json=dados_ipca))

        df = get({"Selic": 11, "IPCA": 433}, last=3)
        assert "Selic" in df.columns
        assert "IPCA" in df.columns


# ============================================================================
# Testes de metadata
# ============================================================================


class TestMetadata:
    @respx.mock
    def test_metadata_basico(self) -> None:
        """Busca metadados de uma série."""
        ultimos_url = ULTIMOS_URL.format(codigo=11, n=1)
        meta_url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{11}"

        respx.get(ultimos_url).mock(
            return_value=httpx.Response(200, json=[{"data": "01/01/2024", "valor": "11.75"}])
        )
        respx.get(meta_url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "nomeCompleto": "Taxa de juros - Selic",
                    "periodicidade": {"nome": "Diária"},
                    "unidadePadrao": {"nome": "% a.a."},
                    "gestorProprietario": {"nome": "BCB-Demab"},
                    "dataInicio": "04/06/1986",
                    "dataFim": None,
                },
            )
        )

        info = metadata(11)
        assert info["codigo"] == 11
        assert info["nome"] == "Taxa de juros - Selic"
        assert info["periodicidade"] == "Diária"

    @respx.mock
    def test_metadata_serie_inexistente(self) -> None:
        """Metadados de série inexistente deve levantar exceção."""
        ultimos_url = ULTIMOS_URL.format(codigo=99999, n=1)
        respx.get(ultimos_url).mock(return_value=httpx.Response(404))

        with pytest.raises(SerieNaoEncontrada):
            metadata(99999)


# ============================================================================
# Testes de formatos de data aceitos
# ============================================================================


class TestFormatosData:
    @respx.mock
    def test_formato_iso(self) -> None:
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(return_value=httpx.Response(200, json=[]))
        df = get(11, start="2024-01-01", end="2024-12-31")
        assert isinstance(df, pd.DataFrame)

    @respx.mock
    def test_formato_brasileiro(self) -> None:
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(return_value=httpx.Response(200, json=[]))
        df = get(11, start="01/01/2024", end="31/12/2024")
        assert isinstance(df, pd.DataFrame)

    @respx.mock
    def test_formato_date_object(self) -> None:
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(return_value=httpx.Response(200, json=[]))
        df = get(11, start=date(2024, 1, 1), end=date(2024, 12, 31))
        assert isinstance(df, pd.DataFrame)
