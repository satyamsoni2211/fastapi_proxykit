from contextlib import asynccontextmanager

from fastapi import APIRouter, Request, Response
import httpx
import pybreaker
import time
import structlog
from opentelemetry.trace import StatusCode
from opentelemetry import metrics

from fast_proxy.models import ProxyConfig, ProxyRoute
from fast_proxy.breaker import create_breaker
from fast_proxy.client import create_http_client
from fast_proxy.errors import ProxyErrorResponse
from fast_proxy.openapi import fetch_target_openapi, merge_openapi_schemas


def proxy_router(config: ProxyConfig) -> APIRouter:
    """Create a pluggable proxy router for a FastAPI app."""
    tracer = config.observability.tracer
    http_client = create_http_client(config.client, tracer_provider=tracer)

    @asynccontextmanager
    async def lifespan(app: APIRouter):
        yield
        await http_client.aclose()

    router = APIRouter(lifespan=lifespan)

    route_map: dict[str, ProxyRoute] = {r.path_prefix: r for r in config.routes}
    breakers: dict[str, pybreaker.CircuitBreaker] = {
        r.path_prefix: create_breaker(r.path_prefix, r.breaker) for r in config.routes
    }

    async def _build_merged_openapi() -> dict:
        """Fetch and merge all target OpenAPI specs."""
        merged = {
            "openapi": "3.1.0",
            "info": {"title": "Proxy API", "version": "1.0.0"},
            "paths": {},
        }
        for route in config.routes:
            if not route.include_in_openapi:
                continue
            openapi_fetch_url = route.openapi_url or f"{route.target_base_url}/openapi.json"
            spec = await fetch_target_openapi(route.target_base_url, openapi_fetch_url)
            if spec:
                merged = merge_openapi_schemas(merged, [spec], route.path_prefix)
            else:
                logger.warning(
                    "proxy.openapi.skipping_route",
                    route=route.path_prefix,
                    reason="fetch_failed",
                )
        return merged

    # Lazily built and cached merged spec
    _cached_openapi: dict | None = None

    @router.get("/openapi.json", include_in_schema=False)
    async def get_openapi(request: Request) -> dict:
        nonlocal _cached_openapi
        if _cached_openapi is None:
            _cached_openapi = await _build_merged_openapi()
        return _cached_openapi

    @router.get("/docs", include_in_schema=False)
    async def get_docs():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    @router.get("/redoc", include_in_schema=False)
    async def get_redoc():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/redoc")

    # Observability instruments
    meter = config.observability.meter
    request_counter = None
    request_latency = None
    if meter:
        request_counter = meter.create_counter(
            name="proxy.requests",
            description="Total proxy requests",
            unit="1",
        )
        request_latency = meter.create_histogram(
            name="proxy.request.duration",
            description="Proxy request duration in seconds",
            unit="s",
        )

    logger = config.observability.logger or structlog.get_logger()

    async def _make_request(
        method: str, target_url: str, request: Request
    ) -> httpx.Response:
        """Bare HTTP request — called inside breaker.call() for circuit management."""
        resp = await http_client.request(
            method=method,
            url=target_url,
            headers=dict(request.headers),
            content=await request.body(),
            params=request.query_params,
        )
        return resp

    @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def proxy_request(path: str, request: Request) -> Response:
        # Longest-prefix match with normalized slashes
        matched_route: ProxyRoute | None = None
        matched_prefix: str | None = None
        for prefix in route_map:
            normalized_prefix = prefix if prefix.startswith("/") else "/" + prefix
            normalized_path = "/" + path
            if normalized_path.startswith(normalized_prefix):
                if matched_prefix is None or len(prefix) > len(matched_prefix):
                    matched_prefix = prefix
                    matched_route = route_map[prefix]

        if matched_route is None:
            return Response(status_code=404, content="No matching route")

        # Strip the matched prefix from the path to get the actual target path
        if matched_route.strip_prefix:
            prefix_len = len(matched_route.path_prefix)
            if not matched_route.path_prefix.startswith("/"):
                prefix_len -= 1
            remaining_path = path[prefix_len:] if len(path) > prefix_len else ""
        else:
            remaining_path = path
        target_url = f"{matched_route.target_base_url.rstrip('/')}/{remaining_path.lstrip('/')}"
        breaker = breakers[matched_route.path_prefix]

        span = None
        if tracer:
            span = tracer.start_span(f"proxy/{matched_route.path_prefix}")
            span.set_attribute("route", matched_route.path_prefix)
            span.set_attribute("target_url", target_url)

        start_time = time.perf_counter()
        try:
            resp = await breaker.call(_make_request, request.method, target_url, request)
            duration = time.perf_counter() - start_time
            result = Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
            if span:
                span.set_attribute("http.status_code", result.status_code)

            if request_counter:
                request_counter.add(1, {"route": matched_route.path_prefix, "status": str(result.status_code)})
            if request_latency:
                request_latency.record(duration, {"route": matched_route.path_prefix})

            logger.info(
                "proxy.request.forwarded",
                route=matched_route.path_prefix,
                method=request.method,
                path=path,
                status_code=result.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            return result
        except pybreaker.CircuitBreakerError as exc:
            duration = time.perf_counter() - start_time
            if span:
                span.set_attribute("http.status_code", 503)
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
            logger.error("proxy.circuit_breaker.open", route=matched_route.path_prefix)
            return Response(
                status_code=503,
                content=ProxyErrorResponse(
                    error="circuit_breaker_open",
                    message="Target service unavailable",
                    route=matched_route.path_prefix,
                ).model_dump_json(),
                media_type="application/json",
            )
        except httpx.TimeoutException as exc:
            breaker.increment_failure()
            if span:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
            logger.error("proxy.timeout", route=matched_route.path_prefix, exc=exc)
            return Response(
                status_code=504,
                content=ProxyErrorResponse(
                    error="timeout",
                    message="Gateway timeout",
                    route=matched_route.path_prefix,
                ).model_dump_json(),
                media_type="application/json",
            )
        except Exception as exc:
            breaker.increment_failure()
            if span:
                span.record_exception(exc)
                span.set_status(StatusCode.ERROR, str(exc))
            logger.error("proxy.error", route=matched_route.path_prefix, exc=exc)
            return Response(
                status_code=503,
                content=ProxyErrorResponse(
                    error="connection_error",
                    message="Target service unavailable",
                    route=matched_route.path_prefix,
                ).model_dump_json(),
                media_type="application/json",
            )
        finally:
            if span:
                span.end()

    return router
