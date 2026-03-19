# fast-proxy

**A production-ready FastAPI plugin that adds transparent HTTP proxy capabilities to any existing application.**

Built with non-blocking I/O, per-route circuit breakers, and full OpenTelemetry observability.

---

## What

`fast-proxy` is a library you drop into an existing FastAPI application. Register it with a configuration object, and it proxies incoming HTTP requests to any target service — preserving path, query, and headers transparently.

```python
from fastapi import FastAPI
from fast_proxy import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig

app = FastAPI()

app.include_router(
    proxy_router(
        ProxyConfig(
            routes=[
                ProxyRoute(
                    path_prefix="/api/users",
                    target_base_url="https://users.example.com",
                    breaker=BreakerConfig(failure_threshold=5, timeout=30),
                    strip_prefix=True,
                ),
            ]
        )
    )
)
```

A request to `GET /api/users/123` → `GET https://users.example.com/123`.

---

## Why

Every non-trivial system needs to proxy requests — microservices behind an API gateway, legacy systems exposed through a modern facade, testing environments forwarding to live backends.

Building a proxy from scratch means solving the same problems every time:

- **Resilience** — When a downstream service is down, you don't want to hammer it with retries or let failures cascade.
- **Observability** — You can't debug what you can't see. Tracing, metrics, and structured logs are not optional.
- **Non-blocking I/O** — Proxying synchronously in a web server blocks threads and limits concurrency.

`fast-proxy` solves these once and gives you a reusable, configurable component instead.

---

## Who

- **Backend developers** building API gateways or reverse proxies in FastAPI
- **Platform/infra engineers** adding proxy routing to existing services
- **Teams migrating architectures** that need to route requests to multiple backend services while maintaining a single API surface

---

## Where

Install from source:

```bash
pip install .
# or with uv
uv pip install .
```

Requires **Python 3.13+**.

---

## When

Use `fast-proxy` when you need to:

- Route requests to one or more target services from a FastAPI app
- Protect downstream services with circuit breakers that open after repeated failures
- Get full observability into proxy traffic (traces, metrics, structured logs)
- Forward requests transparently without re-implementing HTTP client logic

---

## How

### Configuration

```python
from fast_proxy import (
    ProxyConfig,
    ProxyRoute,
    ProxyErrorResponse,
    BreakerConfig,
    ObservabilityConfig,
    ClientConfig,
)

config = ProxyConfig(
    # One or more routes — longest-prefix match is used
    routes=[
        ProxyRoute(
            path_prefix="/api/users",          # Route prefix to match
            target_base_url="https://users.example.com",  # Target base URL
            breaker=BreakerConfig(
                failure_threshold=5,          # Failures before opening circuit
                timeout=30,                    # Seconds before transitioning to half-open
            ),
            strip_prefix=True,                 # Strip /api/users from forwarded path
            openapi_url=None,                  # Override target's OpenAPI URL (optional)
            include_in_openapi=True,           # Include target's paths in merged /docs
        ),
    ],
    # Observability — inject your own OTel handles
    observability=ObservabilityConfig(
        tracer=your_tracer,       # OpenTelemetry tracer (optional)
        meter=your_meter,         # OpenTelemetry meter (optional)
        logger=your_logger,       # structlog or stdlib logger (optional)
    ),
    # HTTP client settings
    client=ClientConfig(
        timeout=10.0,             # Request timeout in seconds
        max_connections=100,      # Max concurrent connections
    ),
)
```

### Registering the router

```python
from fastapi import FastAPI

app = FastAPI()
app.include_router(proxy_router(config))
```

All requests matching a configured `path_prefix` are proxied. Requests matching no prefix return `404`.

### Merged OpenAPI documentation

When a target service exposes an OpenAPI spec at `{target_base_url}/openapi.json`, `fast-proxy` can merge those paths into its own `/docs` endpoint so all routes appear in a single Swagger UI.

For each route with `include_in_openapi=True` (the default), the proxy fetches the target's `/openapi.json` and prefixes all its paths with the route's `path_prefix`:

| Target path | Merged path |
|---|---|
| `/users` | `/api/users` |
| `/users/{id}` | `/api/users/{id}` |

To use this feature, disable FastAPI's default docs when creating your app:

```python
from fastapi import FastAPI

app = FastAPI(
    openapi_url=None,   # Disable default OpenAPI
    docs_url=None,
    redoc_url=None,
)
app.include_router(proxy_router(config))
```

Then visit `/docs` to see all merged routes, or `/openapi.json` for the raw merged spec.

### OpenTelemetry integration

`tracer` and `meter` are injected from the host application's OTel setup, giving you full control over the export pipeline:

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

trace.set_tracer_provider(TracerProvider())
metrics.set_meter_provider(MeterProvider())

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

config = ProxyConfig(
    routes=[...],
    observability=ObservabilityConfig(tracer=tracer, meter=meter),
)
```

### Error responses

When the circuit breaker opens or a downstream service is unreachable, `fast-proxy` returns structured JSON:

```json
{
  "error": "circuit_breaker_open",
  "message": "Target service unavailable",
  "route": "/api/users"
}
```

| Condition | Status | Error code |
|---|---|---|
| Circuit breaker open | 503 | `circuit_breaker_open` |
| Request timeout | 504 | `timeout` |
| Connection error | 503 | `connection_error` |

---

## Design decisions

### Circuit breakers per route

Each `ProxyRoute` gets its own `pybreaker.CircuitBreaker` instance. Failures are counted per route — a failure on `/api/users` never trips the breaker for `/api/orders`.

Breakers are cached by `(route_name, failure_threshold, timeout)` so repeated calls with the same config return the same instance, preserving failure state across requests.

### Non-blocking HTTP

All outbound requests use `httpx.AsyncClient` — fully async, connection-pooled, with configurable limits. The client is created once and closed cleanly on application shutdown via a FastAPI lifespan handler.

### Observability is optional

`tracer`, `meter`, and `logger` are all optional. If not provided, the proxy runs without instrumentation. If provided, every request gets a span with `route`, `target_url`, `http.status_code`, and full exception recording.

Metrics emitted:
- `proxy.requests` (counter) — `route`, `status`
- `proxy.request.duration` (histogram) — `route`

---

## Project layout

```
src/fast_proxy/
├── __init__.py     # Public exports
├── models.py       # Pydantic config models
├── errors.py       # ProxyErrorResponse
├── breaker.py      # Per-route circuit breaker factory (cached)
├── client.py       # Shared httpx.AsyncClient factory
├── openapi.py      # Target OpenAPI spec fetch and merge
└── router.py       # FastAPI APIRouter + proxy handler

examples/
├── api_gateway/     # Multi-service gateway with per-route breakers
├── legacy_facade/  # Wrapping a legacy service behind a modern prefix
└── multi_env/      # Routing to dev/staging/prod environments
```

---

## Examples

Run any example with `uv run python -m uvicorn examples.<name>.main:app --port 8000`.

### API Gateway (`examples/api_gateway/`)

A FastAPI app acting as an API gateway routing to three backend services — users, orders, and products — each with its own circuit breaker config:

```python
from examples.api_gateway.main import create_app

app = create_app(target_base_url="https://api.example.com")
```

Routes: `/api/users` → users service, `/api/orders` → orders service, `/api/products` → products service. Each has different `failure_threshold` and `timeout` values.

### Legacy Facade (`examples/legacy_facade/`)

A single route wrapping a legacy service behind a modern prefix, with a longer timeout:

```python
from examples.legacy_facade.main import create_app

app = create_app(legacy_base_url="https://legacy.internal.com")
```

Route: `/legacy/v1/*` → `https://legacy.internal.com/api/*` (strip_prefix=True). Useful for migrating from legacy systems while maintaining backwards-compatible URLs.

### Multi-Environment (`examples/multi_env/`)

Routing to different environments (dev/staging/prod) based on path prefix:

```python
from examples.multi_env.main import create_app

app = create_app(
    dev_url="https://dev-backend.example.com",
    staging_url="https://staging-backend.example.com",
    prod_url="https://prod-backend.example.com",
)
```

Routes: `/dev/api/*` → dev, `/staging/api/*` → staging, `/api/*` → prod (default).

---

## Testing

```bash
pytest tests/ -v
```

Unit tests cover:
- `models.py` — Pydantic validation (including new `openapi_url`, `include_in_openapi` fields)
- `breaker.py` — circuit breaker creation and caching
- `client.py` — HTTP client factory
- `openapi.py` — OpenAPI spec fetch and merge

Integration tests use `pytest-httpserver` to verify end-to-end request passthrough and OpenAPI merge with a real mock server.

Example tests in `examples/*/test_example.py` verify routing behavior against mock backends.

---

## License

MIT License. See [LICENSE](LICENSE) for full text.
