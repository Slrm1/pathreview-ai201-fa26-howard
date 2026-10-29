# PathReview Contribution Journal

## Unit 7 — Issue selection

**Issue link:** https://github.com/codepath/pathreview-ai201-fa26-howard/issues/62

**Issue title:** Health check references `settings.redis_host`, which does not exist on Settings

**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:** The Redis portion of `GET /health` reads `settings.redis_host` and `settings.redis_port`, but `Settings` only defines `redis_url`. The broad exception handler catches the resulting `AttributeError`, so the endpoint incorrectly reports Redis as unhealthy and can return a 503 even when Redis is reachable. The fix should create the Redis client from `settings.redis_url`, preserve the existing health response behavior, and add focused tests for both a successful ping and a Redis failure. The issue-specific mypy suppression should also be removed once the invalid attribute access is gone.

**Branch name:** `fix/62-redis-health-check`

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [ ] Issue added to cohort ledger

### Issue-selection checklist reasoning

- **Understanding:** I can explain the failure and the expected result: the health route should use the configured Redis URL and report the real ping outcome instead of failing on missing settings fields.
- **Affected code:** I located and read `health_check` in `api/routes/health.py`, the `Settings` definition in `core/config.py`, the router registration in `api/main.py`, and the issue-specific mypy override in `pyproject.toml`.
- **Definition of done:** Use `redis_url` to construct the client, verify healthy and unhealthy Redis outcomes with focused tests, remove the obsolete `attr-defined` suppression, and keep the health endpoint's response contract intact.
- **Tier fit:** This is a Tier 1 change localized to the API health route, its tests, and the narrow type-check configuration. It does not require a cross-module architecture change.
- **Test readiness:** There is no dedicated health-route test in the current suite, so I will add focused coverage following the existing pytest patterns rather than modify unrelated tests.
- **Claims and scope:** The issue is open, has no assignee or comments, and the cohort ledger currently shows 0 claims. I estimate 2–4 focused hours, which fits the Unit 8–9 timeline.
- **Dependencies:** The issue lists no blockers or unresolved dependencies. PostgreSQL and Redis are external services for integration checks, but the route behavior can be tested with mocks.
