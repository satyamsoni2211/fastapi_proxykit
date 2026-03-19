import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_proxykit import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig

@pytest.fixture
def mock_server_with_openapi(httpserver):
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Target Service", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"summary": "List users"}},
            "/users/{id}": {"get": {"summary": "Get user"}}
        }
    }
    httpserver.expect_request("/openapi.json", method="GET").respond_with_json(openapi_spec)
    httpserver.expect_request("/users", method="GET").respond_with_data("users_response", status=200)
    httpserver.expect_request("/users/123", method="GET").respond_with_data("user_123", status=200)
    yield httpserver

def test_openapi_merge_get_openapi_json(mock_server_with_openapi):
    config = ProxyConfig(
        routes=[
            ProxyRoute(
                path_prefix="/api/users",
                target_base_url=mock_server_with_openapi.url_for("/"),
                breaker=BreakerConfig(),
                strip_prefix=True,
                include_in_openapi=True,
            )
        ]
    )
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.include_router(proxy_router(config))
    client = TestClient(app)

    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    # Merged spec contains prefixed paths from target
    assert "/api/users" in spec["paths"]
    assert "/api/users/{id}" in spec["paths"]
    # Target paths without prefix are NOT present
    assert "/users" not in spec["paths"]
