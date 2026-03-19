import httpx
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from fast_proxy.models import ClientConfig


def create_http_client(config: ClientConfig, tracer_provider=None) -> httpx.AsyncClient:
    """Create a shared httpx.AsyncClient with connection pooling and optional OTel instrumentation."""
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(config.timeout),
        limits=httpx.Limits(
            max_connections=config.max_connections,
            max_keepalive_connections=config.max_connections,
        ),
    )
    if tracer_provider:
        HTTPXClientInstrumentor.instrument_client(
            client=client, tracer_provider=tracer_provider
        )
    return client
