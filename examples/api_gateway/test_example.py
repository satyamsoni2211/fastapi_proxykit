import pytest
from fastapi.testclient import TestClient


def test_api_gateway_routes(httpserver):
    from examples.api_gateway.main import create_app

    # Set up mock handlers for all three services
    # Note: create_app appends /users-service, /orders-service, /products-service to target_base_url
    # so we expect requests at those paths, not /users, /orders, /products
    httpserver.expect_request("/users-service/", method="GET").respond_with_data("users_response", status=200)
    httpserver.expect_request("/orders-service/", method="GET").respond_with_data("orders_response", status=200)
    httpserver.expect_request("/products-service/", method="GET").respond_with_data("products_response", status=200)
    # Also handle the user-specific endpoint for the strip_prefix test
    # /api/users/123 -> strip /api/users -> remaining path is 123 -> /users-service/123
    httpserver.expect_request("/users-service/123", method="GET").respond_with_data("user_123_response", status=200)

    app = create_app(httpserver.url_for("/"))
    client = TestClient(app)

    # Test all three routes
    resp_users = client.get("/api/users")
    assert resp_users.status_code == 200
    assert resp_users.text == "users_response"

    resp_orders = client.get("/api/orders")
    assert resp_orders.status_code == 200
    assert resp_orders.text == "orders_response"

    resp_products = client.get("/api/products")
    assert resp_products.status_code == 200
    assert resp_products.text == "products_response"

    # Test strip_prefix: /api/users/123 should forward to /users-service/123 on target
    # (strip_prefix removes /api/users from path, leaving 123, then appends to target_base_url)
    resp_user_123 = client.get("/api/users/123")
    assert resp_user_123.status_code == 200
    assert resp_user_123.text == "user_123_response"