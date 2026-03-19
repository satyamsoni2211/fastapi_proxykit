<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-3775A9?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/pypi/v/fastapi-proxykit?style=for-the-badge&logo=pypi&logoColor=white&color=blue" alt="PyPI version" />
  <img src="https://img.shields.io/pypi/dm/fastapi-proxykit?style=for-the-badge&color=ff69b4" alt="PyPI downloads" />
  <img src="https://img.shields.io/github/license/satyamsoni2211/fastapi_proxykit?style=for-the-badge&color=green" alt="License" />
  <img src="https://img.shields.io/github/stars/satyamsoni2211/fastapi_proxykit?style=for-the-badge&color=yellow" alt="Stars" />
</p>

<h1 align="center">⚡ fastapi-proxykit</h1>

<p align="center">
  <b>Production-ready transparent proxy routes for FastAPI</b><br>
  Turn your FastAPI app into a resilient API gateway with per-route circuit breakers, OpenTelemetry observability, and automatic OpenAPI merging — zero boilerplate.
</p>

<p align="center">
  <a href="https://pypi.org/project/fastapi-proxykit/" target="_blank">
    <img src="https://img.shields.io/badge/Install%20with%20pip-✓-blue?style=for-the-badge&logo=pypi&logoColor=white" alt="Install with pip" />
  </a>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-configuration">Configuration</a> •
  <a href="#-examples">Examples</a> •
  <a href="#-why-use-it">Why?</a> •
  <a href="#-license">License</a>
</p>

<div align="center">
  <img src="https://via.placeholder.com/900x450/0d1117/58a6ff?text=fastapi-proxykit+in+action" alt="fastapi-proxykit architecture" width="900" />
  <!-- Replace with real diagram (Excalidraw recommended) -->
</div>
## ✨ Features

- 🔀 **Transparent proxying** — preserve path, query params, headers automatically
- 🛡️ **Per-route circuit breakers** — isolated resilience with `pybreaker` (no cascading failures)
- 📊 **Full OpenTelemetry support** — tracing, metrics, custom tracer/meter injection
- 📖 **Automatic OpenAPI merging** — unified `/docs` from all backend services
- ⚡ **Non-blocking I/O** — `httpx.AsyncClient` with pooling & configurable limits
- 🧩 **Declarative config** — clean Pydantic-powered routes & settings
- 🛠 **Structured errors** — consistent JSON responses (503 breaker open, 504 timeout, etc.)
- 🔌 **Lifespan-aware** — client auto cleanup on shutdown
- 🆓 **Zero external agents** required for observability

## 🚀 Quick Start

```bash
pip install fastapi-proxykit
# or
uv add fastapi-proxykit
```

```python
from fastapi import FastAPI
from fastapi_proxykit import proxy_router, ProxyConfig, ProxyRoute, BreakerConfig

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
                ProxyRoute(
                    path_prefix="/api/orders",
                    target_base_url="https://orders.example.com",
                    breaker=BreakerConfig(failure_threshold=3, timeout=15),
                ),
            ]
        )
    )
)
```

→ `GET /api/users/42` proxies to `https://users.example.com/42`

## 📦 Installation

```bash
# Recommended — from PyPI
pip install fastapi-proxykit

# Or with uv (faster)
uv pip install fastapi-proxykit

# For development / latest main
pip install git+https://github.com/satyamsoni2211/fastapi_proxykit.git
```

**Requirements**: Python 3.13+

## ⚙️ Configuration

Full power via `ProxyConfig`:

```python
from fastapi_proxykit import ProxyConfig, ProxyRoute, BreakerConfig, ObservabilityConfig, ClientConfig

config = ProxyConfig(
    routes=[
        ProxyRoute(
            path_prefix="/api/v1/users",
            target_base_url="https://users-service.internal",
            strip_prefix=True,
            breaker=BreakerConfig(failure_threshold=5, timeout=30),
            include_in_openapi=True,
        ),
        # ... more routes
    ],
    observability=ObservabilityConfig(
        tracer=your_tracer,   # opentelemetry trace.get_tracer()
        meter=your_meter,     # opentelemetry metrics.get_meter()
        logger=your_logger,   # optional structlog / logging
    ),
    client=ClientConfig(
        timeout=15.0,
        max_connections=200,
    ),
)
```

### Unified OpenAPI (recommended)

```python
app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
app.include_router(proxy_router(config))
```

→ All backend OpenAPI specs merged at `/docs` with prefixed paths.

## 📚 Examples

See the [`examples/`](./examples) folder:

- `api_gateway/` — Multi-service gateway with different breaker settings
- `legacy_facade/` — Modern prefix for legacy backend
- `multi_env/` — Route to dev/staging/prod based on env

Run any example:
```bash
uv run python -m uvicorn examples.api_gateway.main:app --reload --port 8000
```

## 🤔 Why fastapi-proxykit? — Real Developer Benefits

Building proxy/routing logic in FastAPI often means repeating the same boilerplate — manual `httpx` calls, error handling, timeouts, resilience patterns, tracing, and fragmented docs. **fastapi-proxykit** eliminates this repetition with a **single, configurable, production-grade component**.

Here's how it directly benefits you as a developer:

- **Save hours (or days) of repetitive coding**  
  Instead of hand-writing proxy endpoints for every backend service (with custom path handling, headers forwarding, timeouts, etc.), you define routes declaratively once via `ProxyRoute`. Drop it in with `app.include_router(proxy_router(config))` — instant transparent proxying. No more duplicating `async def proxy_xxx(...)` functions.

- **Prevent cascading failures & protect your backends**  
  Per-route circuit breakers (`pybreaker`) isolate failures: if `/api/users` backend flakes out (e.g., 5 failures in a row), that route "opens" automatically — returning fast 503s instead of hanging clients or hammering the failing service. Other routes (e.g., `/api/orders`) keep working normally. This is huge for microservices/gateway patterns — no more "one slow service kills the whole app".

- **Debug & monitor like a pro — zero extra instrumentation**  
  Full OpenTelemetry integration (traces, metrics, optional structured logs) out-of-the-box. Inject your existing tracer/meter/logger — every proxied request gets spans with target URL, status, duration, errors, etc.  
  → Quickly spot slow backends, high-latency routes, error spikes, or retry storms in production. No manual `@tracer.start_as_current_span()` everywhere.

- **Unified Swagger/OpenAPI docs — one `/docs` to rule them all**  
  Automatically fetches each backend's `/openapi.json`, prefixes paths (e.g., `/api/users/*` → shows as `/api/users/...` in UI), and merges into your app's docs.  
  → Developers/consumers see a single, complete API surface instead of jumping between 5+ service docs. Great for internal APIs, partner integrations, or self-documenting gateways.

- **Scale confidently with non-blocking, pooled I/O**  
  Uses `httpx.AsyncClient` under the hood with configurable connection limits, timeouts, and pooling. Fully async — no thread blocking, supports high concurrency without spiking CPU/memory.  
  → Your gateway stays responsive even under heavy load or when proxying many slow backends.

- **Consistent, client-friendly errors — no ugly 502s**  
  Structured JSON responses for failures:  
  ```json
  {"error": "circuit_breaker_open", "message": "Target service temporarily unavailable"}
  ```  
  or 504 on timeout. Easy for frontend/mobile clients to handle gracefully.

- **Clean separation for complex architectures**  
  Ideal for:  
  - **Microservices gateway** — route `/users`, `/orders`, `/payments` to isolated services with different resilience rules  
  - **Legacy modernization** — facade old APIs behind modern prefixes without rewriting clients  
  - **Multi-env routing** — `/dev/*` → dev cluster, `/prod/*` → production  
  - **Observability-first teams** — plug into existing OTEL collectors (Jaeger, Zipkin, Prometheus, etc.) without changing code

In short: **fastapi-proxykit** turns painful, error-prone proxy boilerplate into a **declarative, resilient, observable feature** — letting you focus on business logic instead of infrastructure plumbing.

Many FastAPI developers end up reinventing 80% of this themselves. With proxykit, you get it right the first time — resilient, observable, and maintainable.



| Without proxykit                          | With fastapi-proxykit                          |
|-------------------------------------------|------------------------------------------------|
| Manual httpx per endpoint                 | One config → all routes                        |
| No resilience → cascading failures        | Per-route circuit breakers                     |
| Fragmented /docs per service              | Merged, prefixed OpenAPI in single UI          |
| Custom tracing boilerplate                | Automatic OpenTelemetry spans & metrics        |
| Risk of blocking I/O                      | Fully async + pooled connections               |

## Contributing

Contributions welcome!  
1. Fork the repo  
2. Create feature branch (`git checkout -b feature/amazing-thing`)  
3. Commit (`git commit -m 'Add amazing thing'`)  
4. Push & open PR

## 📄 License

MIT License — see [`LICENSE`](./LICENSE)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/satyamsoni2211">Satyam Soni</a> •
  <a href="https://x.com/_satyamsoni_">@_satyamsoni_</a>
</p>

<p align="center">
  <a href="https://github.com/satyamsoni2211/fastapi_proxykit/issues/new?labels=enhancement&title=Feature+request">Suggest Feature</a>
  ·
  <a href="https://github.com/satyamsoni2211/fastapi_proxykit/issues/new?labels=bug&title=Bug">Report Bug</a>
</p>