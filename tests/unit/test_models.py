import pytest
from fast_proxy.models import ProxyRoute, BreakerConfig

def test_proxy_route_has_openapi_fields():
    route = ProxyRoute(
        path_prefix="/api/users",
        target_base_url="https://users.example.com",
    )
    assert hasattr(route, "openapi_url")
    assert hasattr(route, "include_in_openapi")
    assert route.include_in_openapi is True
    assert route.openapi_url is None