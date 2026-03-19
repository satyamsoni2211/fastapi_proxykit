import pytest
from unittest.mock import MagicMock
from fast_proxy.breaker import create_breaker
from fast_proxy.models import BreakerConfig


class TestCreateBreaker:
    def test_breaker_config_creates_breaker_instance(self):
        config = BreakerConfig(failure_threshold=3, timeout=10)
        breaker = create_breaker("test_route", config)
        assert breaker is not None

    def test_different_routes_get_different_breaker_instances(self):
        config = BreakerConfig()
        breaker1 = create_breaker("route_a", config)
        breaker2 = create_breaker("route_b", config)
        assert breaker1 is not breaker2

    def test_breaker_is_pybreaker_instance(self):
        import pybreaker
        config = BreakerConfig()
        breaker = create_breaker("test", config)
        assert isinstance(breaker, pybreaker.CircuitBreaker)

    def test_breaker_is_cached_for_same_route(self):
        """Same route + same config returns the same breaker instance."""
        config = BreakerConfig(failure_threshold=5, timeout=30)
        breaker1 = create_breaker("cached_route", config)
        breaker2 = create_breaker("cached_route", config)
        assert breaker1 is breaker2  # same cached instance

    def test_different_configs_different_breakers(self):
        """Different configs for same route should return different instances."""
        config1 = BreakerConfig(failure_threshold=3, timeout=10)
        config2 = BreakerConfig(failure_threshold=5, timeout=20)
        breaker1 = create_breaker("same_route", config1)
        breaker2 = create_breaker("same_route", config2)
        assert breaker1 is not breaker2  # different config = different cache key