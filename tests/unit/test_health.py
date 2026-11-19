"""Regression tests for the Redis dependency in the health endpoint."""

import pytest
import redis
from fastapi import HTTPException

from api.routes.health import health_check


class HealthyDatabase:
    """Minimal async database dependency that reports a successful query."""

    async def execute(self, query: str) -> None:
        assert query == "SELECT 1"


class HealthyRedis:
    """Redis stand-in whose ping succeeds when construction is reached."""

    configured_url: str | None = None
    configured_options: dict[str, object] = {}

    @classmethod
    def from_url(cls, url: str, **kwargs) -> "HealthyRedis":
        """Record client configuration and return a healthy client."""
        cls.configured_url = url
        cls.configured_options = kwargs
        return cls()

    def ping(self) -> bool:
        return True


class UnhealthyRedis(HealthyRedis):
    """Redis stand-in whose ping reports a connection failure."""

    def ping(self) -> bool:
        raise redis.ConnectionError("Redis is unavailable")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_uses_configured_redis_url(monkeypatch) -> None:
    """A healthy Redis client should be created from the configured URL."""
    from core.config import settings

    monkeypatch.setattr(redis, "Redis", HealthyRedis)

    result = await health_check(HealthyDatabase())

    assert result["status"] == "healthy"
    assert result["dependencies"]["redis"] == "healthy"
    assert HealthyRedis.configured_url == settings.redis_url
    assert HealthyRedis.configured_options == {"decode_responses": True}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_reports_redis_ping_failure(monkeypatch) -> None:
    """A Redis connection error should retain the structured 503 response."""
    monkeypatch.setattr(redis, "Redis", UnhealthyRedis)

    with pytest.raises(HTTPException) as exc_info:
        await health_check(HealthyDatabase())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["status"] == "unhealthy"
    assert exc_info.value.detail["dependencies"]["redis"] == "unhealthy"
    assert exc_info.value.detail["dependencies"]["postgres"] == "healthy"
    assert exc_info.value.detail["dependencies"]["vector_db"] == "healthy"
