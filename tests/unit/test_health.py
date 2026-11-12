"""Regression test that reproduces issue #62 in the health endpoint."""

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

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def ping(self) -> bool:
        return True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_uses_configured_redis_url(monkeypatch) -> None:
    """A healthy Redis should not be reported unhealthy due to bad settings fields."""
    monkeypatch.setattr(redis, "Redis", HealthyRedis)

    try:
        result = await health_check(HealthyDatabase())
    except HTTPException as exc:
        pytest.fail(
            "Issue #62 reproduced: GET /health returned 503 even though the "
            "database and Redis ping were healthy. The route accesses missing "
            "settings.redis_host/settings.redis_port instead of redis_url. "
            f"Response detail: {exc.detail}"
        )

    assert result["status"] == "healthy"
    assert result["dependencies"]["redis"] == "healthy"
