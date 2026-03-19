"""
Multi-Environment Example — demonstrates routing to different environments.

Routes:
  /dev/api/*     → dev backend
  /staging/api/* → staging backend
  /api/*         → prod backend (default)

This is useful for testing setups where you need to forward to live
backends in different environments from a single proxy.

Run with: python -m uvicorn examples.multi_env.main:app --port 8000
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi import FastAPI
from fastapi_proxykit import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig


def create_app(dev_url: str, staging_url: str, prod_url: str) -> FastAPI:
    config = ProxyConfig(
        routes=[
            ProxyRoute(
                path_prefix="/dev/api",
                target_base_url=dev_url,
                breaker=BreakerConfig(failure_threshold=3, timeout=30),
                strip_prefix=True,
            ),
            ProxyRoute(
                path_prefix="/staging/api",
                target_base_url=staging_url,
                breaker=BreakerConfig(failure_threshold=3, timeout=30),
                strip_prefix=True,
            ),
            ProxyRoute(
                path_prefix="/api",
                target_base_url=prod_url,
                breaker=BreakerConfig(failure_threshold=5, timeout=60),
                strip_prefix=True,
            ),
        ]
    )
    app = FastAPI()
    app.include_router(proxy_router(config))
    return app


if __name__ == "__main__":
    app = create_app(
        dev_url="https://dev-backend.example.com",
        staging_url="https://staging-backend.example.com",
        prod_url="https://prod-backend.example.com",
    )
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)