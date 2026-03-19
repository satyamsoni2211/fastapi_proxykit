import pytest
from fastapi_proxykit.client import create_http_client
from fastapi_proxykit.models import ClientConfig


class TestCreateHttpClient:
    def test_creates_httpx_async_client(self):
        import httpx
        config = ClientConfig(timeout=5.0, max_connections=50)
        client = create_http_client(config)
        assert isinstance(client, httpx.AsyncClient)

    def test_client_has_correct_timeout(self):
        config = ClientConfig(timeout=7.5)
        client = create_http_client(config)
        assert client.timeout.connect == 7.5

    def test_client_creation_succeeds(self):
        import httpx
        config = ClientConfig(timeout=5.0, max_connections=50)
        client = create_http_client(config)
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed
