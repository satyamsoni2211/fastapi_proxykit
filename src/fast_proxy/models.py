from pydantic import BaseModel, Field
from typing import Optional


class BreakerConfig(BaseModel):
    failure_threshold: int = Field(default=5, ge=1, description="Failures before opening circuit")
    timeout: int = Field(default=30, ge=1, description="Seconds before transitioning from open to half-open")


class ObservabilityConfig(BaseModel):
    tracer: Optional[object] = Field(default=None, description="OpenTelemetry tracer")
    meter: Optional[object] = Field(default=None, description="OpenTelemetry meter")
    logger: Optional[object] = Field(default=None, description="standard logger")


class ClientConfig(BaseModel):
    timeout: float = Field(default=10.0, gt=0)
    max_connections: int = Field(default=100, ge=1)


class ProxyRoute(BaseModel):
    path_prefix: str = Field(description="Route path prefix, e.g. /api/users")
    target_base_url: str = Field(description="Target base URL, e.g. https://users.example.com")
    breaker: BreakerConfig = Field(default_factory=BreakerConfig)
    strip_prefix: bool = Field(
        default=False,
        description="Strip path_prefix from forwarded URL (default: forward as-is)",
    )
    openapi_url: Optional[str] = Field(
        default=None,
        description="Override URL for target's OpenAPI spec. "
                    "Defaults to {target_base_url}/openapi.json",
    )
    include_in_openapi: bool = Field(
        default=True,
        description="Include this route's target OpenAPI paths in the proxy's /docs",
    )


class ProxyConfig(BaseModel):
    routes: list[ProxyRoute] = Field(min_length=1)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    client: ClientConfig = Field(default_factory=ClientConfig)
