import pytest
from fastapi.testclient import TestClient

def test_legacy_facade_strips_prefix(httpserver):
    from examples.legacy_facade.main import create_app

    httpserver.expect_request("/api/v1/users", method="GET").respond_with_data("legacy_users", status=200)
    httpserver.expect_request("/api/v1/users/123", method="GET").respond_with_data("legacy_user_123", status=200)

    app = create_app(httpserver.url_for("/"))
    client = TestClient(app)

    # /legacy/v1/users should strip /legacy/v1 and forward to /api/v1/users
    resp = client.get("/legacy/v1/users")
    assert resp.status_code == 200
    assert resp.text == "legacy_users"

    # /legacy/v1/users/123 should forward to /api/v1/users/123
    resp2 = client.get("/legacy/v1/users/123")
    assert resp2.status_code == 200
    assert resp2.text == "legacy_user_123"