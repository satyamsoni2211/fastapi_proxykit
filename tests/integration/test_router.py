import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fast_proxy import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig


@pytest.fixture
def mock_server(httpserver):
    httpserver.expect_request("/foo", method="GET").respond_with_data(
        "target_response", status=200
    )
    yield httpserver


@pytest.fixture
def app(mock_server):
    config = ProxyConfig(
        routes=[
            ProxyRoute(
                path_prefix="/proxy",
                target_base_url=mock_server.url_for("/"),
                breaker=BreakerConfig(failure_threshold=5, timeout=30),
                strip_prefix=True,
            )
        ]
    )
    app = FastAPI()
    app.include_router(proxy_router(config))
    return app


def test_observability_tracer_receives_spans(app, mock_server):
    from unittest.mock import MagicMock

    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_tracer.start_span.return_value = mock_span

    from fast_proxy.models import ObservabilityConfig
    config = ProxyConfig(
        routes=[
            ProxyRoute(
                path_prefix="/proxy",
                target_base_url=mock_server.url_for("/"),
                breaker=BreakerConfig(),
                strip_prefix=True,
            )
        ],
        observability=ObservabilityConfig(tracer=mock_tracer),
    )

    from fast_proxy import proxy_router
    from fastapi import FastAPI
    test_app = FastAPI()
    test_app.include_router(proxy_router(config))
    client = TestClient(test_app)

    client.get("/proxy/foo")

    mock_tracer.start_span.assert_called()
    mock_span.set_attribute.assert_any_call("route", "/proxy")
