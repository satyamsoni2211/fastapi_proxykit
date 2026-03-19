"""
API Gateway Example — demonstrates multi-service routing with per-route circuit breakers.

This FastAPI app acts as an API gateway routing to three backend services:
- /api/users    → users service
- /api/orders   → orders service
- /api/products → products service

Each route has its own circuit breaker with different failure thresholds.

Run with: python -m uvicorn examples.api_gateway.main:app --port 8000
(Requires PYTHONPATH to include project root)
"""
import sys
from pathlib import Path

# Allow importing fast_proxy from source
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi import FastAPI
from fast_proxy import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig


def create_app(target_base_url: str) -> FastAPI:
    """
    Create the API gateway FastAPI app.

    In a real deployment, target_base_url would be different per service.
    Here it is unified for demonstration with a pytest-httpserver.
    """
    config = ProxyConfig(
        routes=[
            ProxyRoute(
                path_prefix="/api/users",
                target_base_url=f"{target_base_url}/users-service",
                breaker=BreakerConfig(failure_threshold=5, timeout=30),
                strip_prefix=True,
            ),
            ProxyRoute(
                path_prefix="/api/orders",
                target_base_url=f"{target_base_url}/orders-service",
                breaker=BreakerConfig(failure_threshold=3, timeout=60),
                strip_prefix=True,
            ),
            ProxyRoute(
                path_prefix="/api/products",
                target_base_url=f"{target_base_url}/products-service",
                breaker=BreakerConfig(failure_threshold=10, timeout=15),
                strip_prefix=True,
            ),
        ]
    )
    app = FastAPI()
    app.include_router(proxy_router(config))
    return app


if __name__ == "__main__":
    # Example usage: python -m uvicorn examples.api_gateway.main:app --port 8000
    app = create_app("https://placeholder.example.com")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)