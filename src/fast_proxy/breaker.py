import functools

import pybreaker

from fast_proxy.models import BreakerConfig


@functools.lru_cache(maxsize=None)
def _create_breaker_cached(
    route_name: str, failure_threshold: int, timeout: int
) -> pybreaker.CircuitBreaker:
    """Cached internal factory — one breaker instance per (route_name, failure_threshold, timeout)."""
    breaker = pybreaker.CircuitBreaker(
        name=route_name,
        fail_max=failure_threshold,
        reset_timeout=timeout,
        exclude=[pybreaker.CircuitBreakerError],
    )
    return breaker


def create_breaker(route_name: str, config: BreakerConfig) -> pybreaker.CircuitBreaker:
    """Create (or return cached) a pybreaker circuit breaker for a given route."""
    return _create_breaker_cached(route_name, config.failure_threshold, config.timeout)
