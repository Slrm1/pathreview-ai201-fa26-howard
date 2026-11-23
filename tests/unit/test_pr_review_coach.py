"""Tests for the extra-credit PR Review Coach."""

import httpx
import pytest

from agent.tools.pr_review_coach import PullRequestReviewCoach

pytestmark = pytest.mark.unit


def _mock_client(pr_payload: dict, files_payload: list[dict]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json=files_payload)
        return httpx.Response(200, json=pr_payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_pr_url_accepts_canonical_url():
    target = PullRequestReviewCoach.parse_pr_url("https://github.com/codepath/pathreview/pull/78")

    assert target.owner == "codepath"
    assert target.repo == "pathreview"
    assert target.number == 78


@pytest.mark.parametrize(
    "url",
    [
        "https://gitlab.com/codepath/pathreview/pull/78",
        "https://github.com/codepath/pathreview",
        "https://github.com/codepath/pathreview/pull/not-a-number",
        "https://github.com/codepath/pathreview/pull/78/files",
    ],
)
def test_parse_pr_url_rejects_noncanonical_urls(url):
    with pytest.raises(ValueError, match="GitHub pull request URL"):
        PullRequestReviewCoach.parse_pr_url(url)


def test_execute_returns_structured_fallback_review():
    client = _mock_client(
        {
            "title": "Fix configured Redis health check",
            "body": "Use the configured Redis URL and preserve the response contract.",
            "changed_files": 2,
            "additions": 34,
            "deletions": 6,
        },
        [
            {
                "filename": "api/routes/health.py",
                "status": "modified",
                "additions": 4,
                "deletions": 3,
                "patch": "@@ -1 +1 @@",
            },
            {
                "filename": "tests/unit/test_health.py",
                "status": "modified",
                "additions": 30,
                "deletions": 3,
                "patch": "@@ -1 +1 @@",
            },
        ],
    )
    coach = PullRequestReviewCoach(http_client=client)

    result = coach.execute(
        {"pr_url": "https://github.com/codepath/pathreview/pull/78", "use_ai": False}
    )

    assert result.success is True
    assert result.data["analysis_mode"] == "deterministic fallback"
    assert result.data["files_reviewed"] == 2
    assert result.data["diff_truncated"] is False
    assert result.data["risks"]
    assert result.data["test_gaps"]
    assert result.data["next_steps"]


def test_execute_flags_missing_tests():
    client = _mock_client(
        {
            "title": "Change API behavior",
            "body": "A focused API update.",
            "changed_files": 1,
            "additions": 12,
            "deletions": 2,
        },
        [
            {
                "filename": "api/routes/reviews.py",
                "status": "modified",
                "additions": 12,
                "deletions": 2,
                "patch": "@@ -1 +1 @@",
            }
        ],
    )

    result = PullRequestReviewCoach(http_client=client).execute(
        {"pr_url": "https://github.com/example/repo/pull/7", "use_ai": False}
    )

    assert result.success is True
    assert "without an accompanying test-file change" in result.data["test_gaps"][0]


def test_context_is_truncated_before_model_input():
    client = _mock_client(
        {
            "title": "Large patch",
            "body": "Large change",
            "changed_files": 1,
            "additions": 100,
            "deletions": 0,
        },
        [
            {
                "filename": "api/routes/reviews.py",
                "status": "modified",
                "additions": 100,
                "deletions": 0,
                "patch": "x" * 2_000,
            }
        ],
    )
    coach = PullRequestReviewCoach(http_client=client, max_diff_chars=300)
    pr, files = coach._fetch_pull_request(coach.parse_pr_url("https://github.com/a/b/pull/1"))

    context, truncated = coach._build_context(pr, files)

    assert truncated is True
    assert context.endswith("[diff truncated]")
    assert len(context) <= 320


def test_execute_reports_not_found_without_exposing_response_body():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(404, json={"secret": "x"}))
    )

    result = PullRequestReviewCoach(http_client=client).execute(
        {"pr_url": "https://github.com/example/repo/pull/9", "use_ai": False}
    )

    assert result.success is False
    assert result.error == "Pull request not found or not publicly accessible"
