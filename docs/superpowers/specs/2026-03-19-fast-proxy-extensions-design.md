# fast-proxy Extensions: Examples & OpenAPI Merge

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add example implementations and a Swagger/OpenAPI merge feature so all proxied routes appear in a single `/docs`.

**Architecture:** Examples are standalone FastAPI apps. The OpenAPI merge is a new `openapi.py` module that fetches and merges target OpenAPI specs at router creation time.

**Tech Stack:** Python 3.13+, FastAPI, httpx, pytest-httpserver

---

## Part 1: Examples Folder

### File Structure

```
examples/
├── api_gateway/
│   └── main.py          # Multiple routes, different breakers per service
├── legacy_facade/
│   └── main.py          # Single route wrapping legacy service
└── multi_env/
    └── main.py          # Environment routing via header/path
```

### Example 1: `api_gateway/main.py`

A FastAPI app acting as an API gateway routing to three backend services: `users`, `orders`, and `products`. Each has its own circuit breaker config.

- Routes:
  - `/api/users/*` → `https://users.example.com/*` (breaker: fail_max=5, timeout=30s)
  - `/api/orders/*` → `https://orders.example.com/*` (breaker: fail_max=3, timeout=60s)
  - `/api/products/*` → `https://products.example.com/*` (breaker: fail_max=10, timeout=15s)
- Demonstrates: longest-prefix routing, per-route breaker isolation
- Uses a mock server (httpx_mock fixture or pytest-httpserver) to make the example self-contained

### Example 2: `legacy_facade/main.py`

A single route wrapping a legacy SOAP/REST service behind a modern API facade. The legacy service is mounted at a different base URL and the proxy strips the prefix.

- Route:
  - `/legacy/v1/*` → `https://legacy.internal.com/api/*` (strip_prefix=True)
- Demonstrates: prefix stripping, wrapping legacy systems
- Shows how to configure a long timeout for slow legacy services

### Example 3: `multi_env/main.py`

Routing requests to different environments (dev/staging/prod) based on an `X-Environment` header or path segment.

- Routes:
  - `/dev/api/*` → `https://dev-backend.example.com/*` (env=dev)
  - `/staging/api/*` → `https://staging-backend.example.com/*` (env=staging)
  - `/api/*` → `https://prod-backend.example.com/*` (default env=prod)
- Demonstrates: environment-based routing, request header passthrough
- Useful for testing setups where you forward to live backends

### Shared Example Convention

All examples:
- Use `fast_proxy` from source (relative import or `sys.path` manipulation)
- Include a comment block explaining what the example demonstrates
- Are runnable with `python examples/<name>/main.py` (using a mock server)
- Have no external service dependencies

---

## Part 2: OpenAPI/Swagger Merge

### New Model Fields (`models.py`)

```python
class ProxyRoute(BaseModel):
    # ... existing fields ...
    openapi_url: Optional[str] = Field(
        default=None,
        description="Override URL for target's OpenAPI spec. "
                    "Defaults to {target_base_url}/openapi.json",
    )
    include_in_openapi: bool = Field(
        default=True,
        description="Include this route's target OpenAPI paths in the proxy's /docs",
    )
```

### New Module: `src/fast_proxy/openapi.py`

```python
async def fetch_target_openapi(
    target_base_url: str,
    explicit_url: str | None,
    timeout: float = 5.0,
) -> dict | None:
    """
    Fetch OpenAPI spec from a target service.

    If explicit_url is provided, use it. Otherwise, construct
    {target_base_url.rstrip('/')}/openapi.json.

    Returns None if the fetch fails or the response is not valid JSON.
    """
```

```python
def merge_openapi_schemas(
    proxy_spec: dict,
    target_specs: list[dict],
    path_prefix: str,
) -> dict:
    """
    Merge target OpenAPI paths into the proxy's OpenAPI schema.

    For each path in target_specs:
      - Prefix the path with path_prefix (e.g., /users → /api/users)
      - Deduplicate: if a path already exists in proxy_spec, skip it
      - Copy the path item and any referenced components (schemas, etc.)

    Returns the merged spec dict.
    """
```

### Modified: `src/fast_proxy/router.py`

In `proxy_router(config)`:

1. Build a list of `(path_prefix, target_base_url, openapi_url)` for each route where `include_in_openapi=True`
2. Create the `APIRouter` with `include_router(..., merged_openapi=...)` — or, since FastAPI routers don't natively accept merged specs, instead:
   - Create the router normally
   - Override `router.default_docs` or intercept `/docs` and `/openapi.json` routes explicitly
   - **Approach:** Add explicit routes to the router for `/{path:path}` with `path in ("docs", "openapi.json", "redoc")` that return the merged OpenAPI response

3. On router creation (inside the lifespan or at first `/docs` request):
   ```python
   merged_spec = {"openapi": "3.1.0", "info": {...}, "paths": {}}
   for route in config.routes:
       if not route.include_in_openapi:
           continue
       target_url = route.openapi_url or f"{route.target_base_url}/openapi.json"
       spec = await fetch_target_openapi(route.target_base_url, target_url)
       if spec:
           merged_spec = merge_openapi_schemas(merged_spec, spec, route.path_prefix)
   ```

4. Graceful degradation: if a target is unreachable, log a warning and exclude that route's paths from the merged spec. The proxy's own routes still appear.

### Modified: `src/fast_proxy/__init__.py`

Export any new public symbols (none expected — internal module).

---

## Testing

### Examples

- Each example directory has a `test_example.py` that:
  - Starts a mock HTTP server with known endpoints and OpenAPI spec
  - Imports the example's `app` factory
  - Verifies the proxy routes resolve correctly
  - Tests circuit breaker behavior

### OpenAPI Merge

- **Unit tests** (`tests/unit/test_openapi.py`):
  - `fetch_target_openapi` — successful fetch, 404 fallback, timeout, invalid JSON
  - `merge_openapi_schemas` — basic merge, prefix application, deduplication, component copying

- **Integration tests** (`tests/integration/test_openapi_merge.py`):
  - Mock server serves an OpenAPI spec at `/openapi.json`
  - Proxy router is created with a route pointing to that server
  - `GET /openapi.json` returns merged spec with both proxy and target paths
  - `GET /docs` serves Swagger UI with merged spec

---

## Error Handling

- Target OpenAPI fetch fails → log warning, exclude that route's paths from merged spec, proxy continues
- Target OpenAPI fetch times out → same graceful degradation
- Conflicting path names → skip (don't overwrite), log at debug level
- No routes with `include_in_openapi=True` → serve standard FastAPI OpenAPI spec

---

## Out of Scope

- Recursive `$ref` resolution in OpenAPI merge
- Schema/component deduplication across targets (may cause name collisions)
- Authentication to target OpenAPI endpoints
