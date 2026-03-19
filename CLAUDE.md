# fastapi-proxykit

Production-ready transparent proxy routes for FastAPI with per-route circuit breakers and OpenTelemetry observability.

## Project Structure

```
src/fastapi_proxykit/
├── __init__.py     # Public exports
├── models.py       # Pydantic config: ProxyConfig, ProxyRoute, BreakerConfig, etc.
├── errors.py       # ProxyErrorResponse
├── breaker.py      # Per-route pybreaker factory (cached with lru_cache)
├── client.py       # httpx.AsyncClient factory with OTel instrumentation
├── openapi.py      # Target OpenAPI spec fetch and merge
└── router.py       # FastAPI APIRouter + proxy handler

examples/
├── api_gateway/    # Multi-service gateway
├── legacy_facade/  # Wrapping legacy services
└── multi_env/      # Dev/staging/prod routing
```

## Key Patterns

- **Package import**: `from fastapi_proxykit import proxy_router, ProxyConfig, ...`
- **Breaker caching**: `create_breaker()` uses `@functools.lru_cache` — same config = same instance
- **httpx.AsyncClient**: NOT a context manager for `.request()` — call `await client.request(...)` directly
- **Circuit breaker**: `breaker.call(fn, *args)` — callable + args, NOT lambda; `breaker.increment_failure()` for manual signaling
- **OpenAPI merge**: `include_in_openapi=True` on each `ProxyRoute` — fetched lazily on first `/openapi.json` request
- **Route matching**: longest-prefix match with slash normalization
- **Tests**: use `pytest-httpserver` for mock HTTP servers, `uv run pytest` to run
- **License**: MIT
