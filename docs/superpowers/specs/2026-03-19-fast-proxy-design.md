# Fast-Proxy Design

## Overview

`fast-proxy` is a FastAPI plugin (pluggable `APIRouter`) that adds transparent HTTP proxy functionality to any existing FastAPI application. Host apps include the proxy via `app.include_router(proxy_router(config))`.

## Architecture

```
Existing FastAPI App
      │
      ├── app.include_router(proxy_router(ProxyConfig(...)))
      │
      ▼
ProxyRouter (FastAPI APIRouter)
      │
      ├── Routing Layer (Path → ProxyRoute lookup)
      │
      ├── Circuit Breaker (pybreaker per route)
      │
      ├── httpx.AsyncClient (non-blocking transport)
      │
      └── Target Service
```

Components:
- **ProxyRouter** — Pluggable FastAPI `APIRouter`, self-contained
- **ProxyConfig** — Pydantic model, passed at registration time
- **ProxyRoute** — Maps one or more path prefixes to a target base URL with its own circuit breaker
- **httpx.AsyncClient** — Non-blocking async HTTP transport with connection pooling
- **pybreaker** — Per-route circuit breaker

## Configuration Model

```python
ProxyConfig(
    routes=[
        ProxyRoute(
            path_prefix="/api/users",
            target_base_url="https://users.example.com",
            breaker=BreakerConfig(failure_threshold=5, timeout=30),
        ),
    ],
    observability=ObservabilityConfig(
        tracer=None,    # Injected by host app (OpenTelemetry tracer)
        meter=None,     # Injected by host app (OpenTelemetry meter)
        logger=None,    # Injected by host app (standard logger)
    ),
    client=ClientConfig(timeout=10.0, max_connections=100),
)
```

Observability handles are injected so the host app controls the full observability pipeline (OTLP exporter, Prometheus push gateway, structured logger, etc.).

## Behavior

### Proxy Pass-Through
- Incoming request path + query are forwarded to `{target_base_url}{path}{query}` verbatim
- All HTTP methods are supported
- Request headers are forwarded with optional filtering
- Response body is streamed back to the client

### Circuit Breaker (per route)
- **Closed**: Normal operation; failures increment a counter
- **Open**: After `failure_threshold` consecutive failures, subsequent requests return `503` immediately
- **Half-Open**: After `timeout` seconds, one probe request is sent; success resets to Closed, failure re-opens

### Error Responses
| Condition | HTTP Status | Body |
|-----------|-------------|------|
| Circuit breaker open | 503 | `{"error": "circuit_breaker_open", "message": "Target service unavailable", "route": "..."}` |
| Target timeout | 504 | `{"error": "timeout", "message": "Gateway timeout", "route": "..."}` |
| Target connection error | 503 | `{"error": "connection_error", "message": "...", "route": "..."}` |

### Observability
- **Tracing**: OpenTelemetry spans cover each proxy request with route, target, status, and duration attributes
- **Metrics**: Request count, latency histogram, circuit breaker state gauge — exposed via OpenTelemetry meter
- **Logging**: Structured logs at INFO (request received/forwarded) and ERROR (breaker open, target error) levels using the injected logger

## Non-Blocking Design
- All outbound HTTP calls use `httpx.AsyncClient` — fully async, no thread blocking
- Shared `httpx.AsyncClient` instance with configurable connection pooling
- Async/await throughout the request path

## Testing Strategy
- **Unit tests**: Route matching, URL construction, circuit breaker state transitions, error response mapping
- **Integration tests**: Mock HTTP server + real `httpx.AsyncClient` for end-to-end passthrough verification
