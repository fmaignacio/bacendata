"""
Testes da API REST FastAPI.

Usa httpx.AsyncClient + respx para mockar as chamadas à API do BACEN.
"""

from unittest.mock import patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from bacendata.api.app import create_app
from bacendata.wrapper import cache
from bacendata.wrapper.bacen_sgs import BASE_URL, ULTIMOS_URL

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def desativar_cache():
    """Garante cache desativado em todos os testes da API."""
    cache._ativo = False
    cache._conn = None
    yield
    cache._ativo = False
    cache._conn = None


@pytest.fixture
def app():
    """Cria app FastAPI para testes (sem cache)."""
    with patch("bacendata.api.app.settings") as mock_settings:
        mock_settings.app_name = "BacenData API"
        mock_settings.app_version = "0.2.0"
        mock_settings.rate_limit_free = 100
        mock_settings.rate_limit_pro = 10_000
        mock_settings.cache_ativo = False
        application = create_app()
    return application


@pytest.fixture
def client(app):
    """Client síncrono para testes."""
    return TestClient(app)


def _mock_dados_sgs(codigo: int, dados: list) -> None:
    """Helper: configura mock para endpoint SGS."""
    url = BASE_URL.format(codigo=codigo)
    respx.get(url).mock(return_value=httpx.Response(200, json=dados))


def _mock_dados_ultimos(codigo: int, n: int, dados: list) -> None:
    """Helper: configura mock para endpoint últimos N."""
    url = ULTIMOS_URL.format(codigo=codigo, n=n)
    respx.get(url).mock(return_value=httpx.Response(200, json=dados))


DADOS_SELIC = [
    {"data": "02/01/2024", "valor": "11.65"},
    {"data": "03/01/2024", "valor": "11.65"},
    {"data": "04/01/2024", "valor": "11.65"},
]

DADOS_IPCA = [
    {"data": "01/01/2024", "valor": "0.42"},
    {"data": "01/02/2024", "valor": "0.83"},
]


# ============================================================================
# Testes do Health Check
# ============================================================================


class TestHealthCheck:
    def test_health_ok(self, client: TestClient) -> None:
        """Health check retorna status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["servico"] == "BacenData API"
        assert "versao" in data

    def test_health_sem_rate_limit(self, client: TestClient) -> None:
        """Health check não é afetado por rate limiting."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200


# ============================================================================
# Testes de consulta de série
# ============================================================================


class TestGetSerie:
    @respx.mock
    def test_get_serie_por_codigo(self, client: TestClient) -> None:
        """GET /api/v1/series/{codigo} retorna dados da série."""
        _mock_dados_sgs(11, DADOS_SELIC)

        response = client.get("/api/v1/series/11?start=2024-01-01&end=2024-12-31")
        assert response.status_code == 200

        data = response.json()
        assert data["codigo"] == 11
        assert data["total"] == 3
        assert len(data["dados"]) == 3
        assert data["dados"][0]["valor"] == 11.65

    @respx.mock
    def test_get_serie_por_nome(self, client: TestClient) -> None:
        """GET /api/v1/series/selic retorna dados usando nome do catálogo."""
        _mock_dados_sgs(11, DADOS_SELIC)

        response = client.get("/api/v1/series/selic?start=2024-01-01&end=2024-12-31")
        assert response.status_code == 200

        data = response.json()
        assert data["codigo"] == 11
        assert data["nome"] == "Selic diária"

    @respx.mock
    def test_get_serie_com_last(self, client: TestClient) -> None:
        """GET /api/v1/series/{codigo}?last=N retorna últimos N valores."""
        _mock_dados_ultimos(433, 2, DADOS_IPCA)

        response = client.get("/api/v1/series/433?last=2")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 2
        assert data["codigo"] == 433

    @respx.mock
    def test_get_serie_nao_encontrada(self, client: TestClient) -> None:
        """Série inexistente retorna 404."""
        url = BASE_URL.format(codigo=99999)
        respx.get(url).mock(return_value=httpx.Response(404, text="Série não encontrada"))

        response = client.get("/api/v1/series/99999?start=2024-01-01&end=2024-12-31")
        assert response.status_code == 404

    def test_get_serie_nome_invalido(self, client: TestClient) -> None:
        """Nome inexistente retorna 400."""
        response = client.get("/api/v1/series/serie_inexistente?start=2024-01-01&end=2024-12-31")
        assert response.status_code == 400

    @respx.mock
    def test_get_serie_retorna_info_catalogo(self, client: TestClient) -> None:
        """Série do catálogo inclui nome, periodicidade e unidade."""
        _mock_dados_sgs(11, DADOS_SELIC)

        response = client.get("/api/v1/series/11?start=2024-01-01&end=2024-12-31")
        data = response.json()

        assert data["nome"] == "Selic diária"
        assert data["periodicidade"] == "diária"
        assert data["unidade"] == "% a.a."


# ============================================================================
# Testes de metadados
# ============================================================================


class TestMetadata:
    @respx.mock
    def test_get_metadata(self, client: TestClient) -> None:
        """GET /api/v1/series/{codigo}/metadata retorna metadados."""
        # Mock do endpoint ultimos/1 (validação)
        ultimos_url = ULTIMOS_URL.format(codigo=433, n=1)
        respx.get(ultimos_url).mock(return_value=httpx.Response(200, json=DADOS_IPCA[:1]))

        # Mock do endpoint de metadados
        meta_url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433"
        respx.get(meta_url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "nomeCompleto": "IPCA - Variação mensal",
                    "unidadePadrao": {"nome": "% a.m."},
                    "periodicidade": {"nome": "Mensal"},
                    "gestorProprietario": {"nome": "IBGE"},
                    "dataInicio": "01/01/1980",
                    "dataFim": "01/01/2025",
                },
            )
        )

        response = client.get("/api/v1/series/433/metadata")
        assert response.status_code == 200

        data = response.json()
        assert data["codigo"] == 433
        assert data["nome"] == "IPCA - Variação mensal"
        assert data["periodicidade"] == "Mensal"


# ============================================================================
# Testes do catálogo
# ============================================================================


class TestCatalogo:
    def test_listar_catalogo(self, client: TestClient) -> None:
        """GET /api/v1/catalogo retorna todas as séries."""
        response = client.get("/api/v1/catalogo")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 14
        assert len(data["series"]) == 14

        # Verificar que Selic está na lista
        codigos = [s["codigo"] for s in data["series"]]
        assert 11 in codigos
        assert 433 in codigos

    def test_search_catalogo_por_nome(self, client: TestClient) -> None:
        """GET /api/v1/catalogo/search?q=selic retorna séries com 'selic'."""
        response = client.get("/api/v1/catalogo/search?q=selic")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 1
        codigos = [s["codigo"] for s in data["series"]]
        assert 11 in codigos

    def test_search_catalogo_por_alias(self, client: TestClient) -> None:
        """Busca por alias funciona."""
        response = client.get("/api/v1/catalogo/search?q=dolar")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] >= 1
        codigos = [s["codigo"] for s in data["series"]]
        assert 1 in codigos

    def test_search_catalogo_sem_resultado(self, client: TestClient) -> None:
        """Busca sem resultado retorna lista vazia."""
        response = client.get("/api/v1/catalogo/search?q=xyzabc123")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0
        assert data["series"] == []

    def test_catalogo_inclui_aliases(self, client: TestClient) -> None:
        """Séries do catálogo incluem aliases."""
        response = client.get("/api/v1/catalogo")
        data = response.json()

        # Encontrar Selic
        selic = next(s for s in data["series"] if s["codigo"] == 11)
        assert "selic" in selic["aliases"]
        assert "selic_diaria" in selic["aliases"]


# ============================================================================
# Testes do bulk
# ============================================================================


class TestBulk:
    @respx.mock
    def test_bulk_request(self, client: TestClient) -> None:
        """POST /api/v1/series/bulk retorna múltiplas séries."""
        _mock_dados_sgs(11, DADOS_SELIC)
        _mock_dados_sgs(433, DADOS_IPCA)

        body = {
            "series": [
                {"codigo": 11, "nome": "Selic"},
                {"codigo": 433, "nome": "IPCA"},
            ],
            "start": "2024-01-01",
            "end": "2024-12-31",
        }

        response = client.post("/api/v1/series/bulk", json=body)
        assert response.status_code == 200

        data = response.json()
        assert data["total_series"] == 2
        assert len(data["series"]) == 2

        # Verificar dados individuais
        selic = next(s for s in data["series"] if s["codigo"] == 11)
        ipca = next(s for s in data["series"] if s["codigo"] == 433)
        assert selic["total"] == 3
        assert ipca["total"] == 2

    @respx.mock
    def test_bulk_com_last(self, client: TestClient) -> None:
        """Bulk com last retorna últimos N valores."""
        _mock_dados_ultimos(11, 3, DADOS_SELIC)
        _mock_dados_ultimos(433, 3, DADOS_IPCA)

        body = {
            "series": [
                {"codigo": 11},
                {"codigo": 433},
            ],
            "last": 3,
        }

        response = client.post("/api/v1/series/bulk", json=body)
        assert response.status_code == 200
        assert response.json()["total_series"] == 2

    def test_bulk_vazio(self, client: TestClient) -> None:
        """Bulk com lista vazia retorna 422."""
        body = {"series": []}
        response = client.post("/api/v1/series/bulk", json=body)
        assert response.status_code == 422

    def test_bulk_maximo_20(self, client: TestClient) -> None:
        """Bulk com mais de 20 séries retorna 422."""
        body = {
            "series": [{"codigo": i} for i in range(21)],
            "start": "2024-01-01",
        }
        response = client.post("/api/v1/series/bulk", json=body)
        assert response.status_code == 422


# ============================================================================
# Testes de autenticação
# ============================================================================


class TestAuth:
    def test_acesso_sem_api_key(self, client: TestClient) -> None:
        """Sem API keys configuradas, acesso livre."""
        response = client.get("/api/v1/catalogo")
        assert response.status_code == 200

    @respx.mock
    def test_rate_limit_headers(self, client: TestClient) -> None:
        """Respostas incluem headers de rate limit."""
        _mock_dados_sgs(11, DADOS_SELIC)

        response = client.get("/api/v1/series/11?start=2024-01-01&end=2024-12-31")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


# ============================================================================
# Testes de erro
# ============================================================================


class TestErros:
    @respx.mock
    def test_bacen_api_timeout(self, client: TestClient) -> None:
        """Timeout na API do BACEN retorna 502."""
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(side_effect=httpx.ConnectTimeout("timeout"))

        response = client.get("/api/v1/series/11?start=2024-01-01&end=2024-12-31")
        assert response.status_code == 502

    @respx.mock
    def test_bacen_api_500(self, client: TestClient) -> None:
        """Erro 500 do BACEN retorna 502."""
        url = BASE_URL.format(codigo=11)
        respx.get(url).mock(return_value=httpx.Response(500, text="Internal Server Error"))

        response = client.get("/api/v1/series/11?start=2024-01-01&end=2024-12-31")
        assert response.status_code == 502


# ============================================================================
# Testes do Webhook Stripe
# ============================================================================


class TestWebhookStripe:
    def _checkout_event(self, email="user@example.com", price_id="price_1T2jtH2cO5c0PQGeWxzZVHZb"):
        """Helper: cria evento checkout.session.completed do Stripe."""
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "customer_email": email,
                    "line_items": {
                        "data": [{"price": {"id": price_id}}]
                    },
                    "metadata": {},
                }
            },
        }

    def test_webhook_checkout_gera_api_key(self, client: TestClient, tmp_path) -> None:
        """Webhook de checkout gera API key e retorna."""
        from bacendata.api.routes import webhook

        webhook.KEYS_FILE = tmp_path / "api_keys.json"

        event = self._checkout_event()
        response = client.post("/webhook/stripe", json=event)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["plano"] == "pro"
        assert data["email"] == "user@example.com"
        assert data["api_key"].startswith("bcd_")
        assert len(data["api_key"]) == 52  # "bcd_" + 48 hex chars

    def test_webhook_enterprise(self, client: TestClient, tmp_path) -> None:
        """Webhook com price enterprise retorna plano enterprise."""
        from bacendata.api.routes import webhook

        webhook.KEYS_FILE = tmp_path / "api_keys.json"

        event = self._checkout_event(price_id="price_1T2ju62cO5c0PQGeKXGVEFER")
        response = client.post("/webhook/stripe", json=event)
        assert response.status_code == 200
        assert response.json()["plano"] == "enterprise"

    def test_webhook_persiste_key(self, client: TestClient, tmp_path) -> None:
        """API key é salva no arquivo JSON."""
        import json
        from bacendata.api.routes import webhook

        webhook.KEYS_FILE = tmp_path / "api_keys.json"

        event = self._checkout_event(email="teste@bacendata.com")
        response = client.post("/webhook/stripe", json=event)
        api_key = response.json()["api_key"]

        # Verificar arquivo
        keys = json.loads(webhook.KEYS_FILE.read_text())
        assert api_key in keys
        assert keys[api_key]["plano"] == "pro"
        assert keys[api_key]["email"] == "teste@bacendata.com"

    def test_webhook_ignora_outros_eventos(self, client: TestClient) -> None:
        """Eventos que não são checkout são ignorados."""
        event = {"type": "payment_intent.succeeded", "data": {"object": {}}}
        response = client.post("/webhook/stripe", json=event)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_webhook_payload_invalido(self, client: TestClient) -> None:
        """Payload inválido retorna 400."""
        response = client.post(
            "/webhook/stripe",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400
