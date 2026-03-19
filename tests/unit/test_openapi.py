import pytest
from fastapi_proxykit.openapi import fetch_target_openapi, merge_openapi_schemas

@pytest.mark.asyncio
async def test_fetch_target_openapi_success(httpserver):
    """fetch_target_openapi returns spec dict when target serves valid OpenAPI."""
    openapi_spec = {
        "openapi": "3.1.0",
        "info": {"title": "Target", "version": "1.0.0"},
        "paths": {"/users": {"get": {"summary": "List users"}}}
    }
    httpserver.expect_request("/openapi.json", method="GET").respond_with_json(openapi_spec)

    result = await fetch_target_openapi(
        target_base_url=httpserver.url_for("/"),
        explicit_url=None,
    )
    assert result is not None
    assert result["info"]["title"] == "Target"
    assert "/users" in result["paths"]

@pytest.mark.asyncio
async def test_fetch_target_openapi_returns_none_on_failure():
    """fetch_target_openapi returns None when target is unreachable."""
    result = await fetch_target_openapi(
        target_base_url="http://localhost:99999",
        explicit_url=None,
    )
    assert result is None

def test_merge_openapi_schemas_basic():
    proxy_spec = {
        "openapi": "3.1.0",
        "info": {"title": "Proxy", "version": "1.0.0"},
        "paths": {}
    }
    target_spec = {
        "openapi": "3.1.0",
        "info": {"title": "Target", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"summary": "Get users"}},
            "/users/{id}": {"get": {"summary": "Get user"}}
        }
    }
    result = merge_openapi_schemas(proxy_spec, [target_spec], "/api/users")
    assert "/api/users" in result["paths"]
    assert "/api/users/{id}" in result["paths"]
    assert "/users" not in result["paths"]

def test_merge_openapi_schemas_deduplication():
    proxy_spec = {
        "openapi": "3.1.0",
        "info": {"title": "Proxy", "version": "1.0.0"},
        "paths": {
            "/api/users": {"get": {"summary": "Proxy route"}}
        }
    }
    target_spec = {
        "openapi": "3.1.0",
        "info": {"title": "Target", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"summary": "Target route"}}
        }
    }
    result = merge_openapi_schemas(proxy_spec, [target_spec], "/api/users")
    # Should keep proxy's route, not overwrite
    assert result["paths"]["/api/users"]["get"]["summary"] == "Proxy route"