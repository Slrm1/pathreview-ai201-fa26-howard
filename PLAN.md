# Solution plan

**Issue:** [Health check references `settings.redis_host`, which does not exist on Settings (#62)](https://github.com/codepath/pathreview-ai201-fa26-howard/issues/62)

## Understand

The Redis portion of `health_check()` in `api/routes/health.py` constructs a client with `settings.redis_host` and `settings.redis_port`. The `Settings` class in `core/config.py` defines only `redis_url`, so evaluating either missing attribute raises `AttributeError` before a Redis connection is attempted. The route's broad `except Exception` catches that programming error, marks Redis and the whole service unhealthy, and raises HTTP 503 even when the configured Redis instance is reachable.

Expected behavior: the route should construct its Redis client from the supported `settings.redis_url`, call `ping()`, mark Redis healthy when the ping succeeds, and preserve the current 503 response contract when the ping fails.

Actual behavior: the route always reports Redis unhealthy because it reads configuration fields that do not exist.

## Map

Files involved:

- `api/routes/health.py` — change Redis client construction inside `health_check()`.
- `core/config.py` — source of truth for the existing `redis_url` setting; inspect only, with no schema change expected.
- `tests/unit/test_health.py` — keep the reproduction test and expand it into focused success and failure regression tests.
- `pyproject.toml` — remove the obsolete `attr-defined` mypy suppression for `api.routes.health` while retaining unrelated suppressions still required by that module.

Functions and interfaces involved:

- `api.routes.health.health_check()`
- `redis.Redis.from_url()`
- `core.config.Settings.redis_url`
- FastAPI's existing `HTTPException(status_code=503, detail=health_status)` response path

## Plan

1. Replace the host/port Redis constructor in `health_check()` with `redis.Redis.from_url(settings.redis_url, decode_responses=True)`, keeping the current synchronous `ping()` call and response shape unchanged.
2. Refactor `tests/unit/test_health.py` so the healthy-path test asserts that `from_url()` receives the configured URL and that a successful ping produces `status == "healthy"` and `dependencies.redis == "healthy"`.
3. Add a Redis-failure test whose fake client raises a connection error from `ping()`; assert that `health_check()` raises HTTP 503 and that the response detail marks Redis and the overall service unhealthy.
4. Keep PostgreSQL and vector-database behavior isolated in both tests with a successful fake database dependency and the existing non-empty vector DB URL, ensuring failures are attributable only to Redis.
5. Run the focused health tests, the complete unit suite, Ruff, and mypy. Once mypy confirms the invalid attribute access is gone, remove `attr-defined` from the `api.routes.health` override in `pyproject.toml` without changing the remaining `call-overload` and `index` suppressions unless they are independently proven obsolete.

## Inputs & outputs

**Inputs**

- `settings.redis_url`, including its scheme, host, port, credentials, database number, and optional query parameters.
- The result of the Redis client's `ping()`.
- The existing injected asynchronous database dependency.

**Outputs**

- A Redis client created from the complete configured URL.
- HTTP 200 with the existing health payload when PostgreSQL, Redis, and the critical checks succeed.
- HTTP 503 with the existing structured `detail` payload when Redis is unreachable or its ping raises an exception.
- Focused regression tests that fail on the current bug and pass after the fix.
- A narrower mypy override that no longer hides nonexistent Settings attributes.

## Risks & unknowns

- `redis.Redis.from_url()` may parse credentials, TLS schemes, database numbers, and query parameters differently from a host/port constructor; tests should assert URL forwarding without duplicating redis-py's parsing logic.
- The health route uses the synchronous Redis client inside an async endpoint. This issue only corrects configuration use; changing to `redis.asyncio` would broaden scope and should be handled separately if blocking becomes measurable.
- The broad exception handler intentionally converts Redis client and connection errors into the current 503 contract. The change must not allow a connection exception to escape as HTTP 500.
- `api.routes.health` has additional mypy suppressions. Removing the entire override could expose unrelated baseline errors, so only `attr-defined` should be removed after checking the exact mypy output.
- The repository currently lacks dedicated health-route tests. The tests should call the route function directly to avoid startup hooks or external PostgreSQL/Redis services obscuring this targeted behavior.

## Edge cases

- Redis URL includes a password or username.
- Redis URL selects a nonzero database such as `redis://localhost:6379/3`.
- Redis URL uses TLS via `rediss://`.
- Redis `ping()` returns successfully.
- Redis `ping()` raises a connection or timeout error.
- PostgreSQL is unhealthy while Redis is healthy; the response must remain 503 for the PostgreSQL failure.
- The vector DB URL is empty; it should retain the existing `"unavailable"` behavior without incorrectly changing overall status.
- Redis URL is malformed; client construction should be caught and represented as an unhealthy dependency using the existing response contract.
