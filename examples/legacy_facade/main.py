"""
Legacy Facade Example — demonstrates wrapping a legacy service behind a modern prefix.

Proxies /legacy/v1/* → {target_base_url}/api/* (strip_prefix=True).

This pattern is useful for migrating from legacy systems while maintaining
backwards-compatible URLs.

Run with: python -m uvicorn examples.legacy_facade.main:app --port 8000
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi import FastAPI
from fastapi_proxykit import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig, ClientConfig


def create_app(legacy_base_url: str) -> FastAPI:
    config = ProxyConfig(
        routes=[
            ProxyRoute(
                path_prefix="/legacy/v1",
                target_base_url=f"{legacy_base_url}/api/v1",
                breaker=BreakerConfig(failure_threshold=3, timeout=60),
                strip_prefix=True,
            ),
        ],
        client=ClientConfig(timeout=30.0),  # Longer timeout for legacy service
    )
    app = FastAPI()
    app.include_router(proxy_router(config))
    return app


if __name__ == "__main__":
    app = create_app("https://legacy.internal.com")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)