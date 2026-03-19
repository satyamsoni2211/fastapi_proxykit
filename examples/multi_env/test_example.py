import pytest
from fastapi.testclient import TestClient


def test_multi_env_routing(httpserver):
    from examples.multi_env.main import create_app

    # Mock servers for each environment
    # The proxy strips /api prefix and forwards to prod_url (which is /prod)
    # So /api/users -> /prod/users on the target
    httpserver.expect_request("/prod/users", method="GET").respond_with_data("prod_users", status=200)
    httpserver.expect_request("/prod/orders", method="GET").respond_with_data("prod_orders", status=200)

    app = create_app(
        dev_url=httpserver.url_for("/dev"),
        staging_url=httpserver.url_for("/staging"),
        prod_url=httpserver.url_for("/prod"),
    )
    client = TestClient(app)

    # Default is prod
    resp = client.get("/api/users")
    assert resp.status_code == 200
    assert resp.text == "prod_users"


def test_multi_env_dev_routing(httpserver):
    from examples.multi_env.main import create_app

    # Mock dev backend
    httpserver.expect_request("/dev/users", method="GET").respond_with_data("dev_users", status=200)

    app = create_app(
        dev_url=httpserver.url_for("/dev"),
        staging_url="http://staging.example.com",
        prod_url="http://prod.example.com",
    )
    client = TestClient(app)

    resp = client.get("/dev/api/users")
    assert resp.status_code == 200
    assert resp.text == "dev_users"