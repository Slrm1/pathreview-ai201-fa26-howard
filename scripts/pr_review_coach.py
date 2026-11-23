"""Command-line demonstration for the PathReview PR Review Coach."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.tools.pr_review_coach import PullRequestReviewCoach


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate structured coaching feedback for a public GitHub pull request."
    )
    parser.add_argument("pr_url", help="Public URL such as https://github.com/org/repo/pull/123")
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use the deterministic fallback even when an LLM key is configured.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Read a saved {pr, files} JSON payload for an offline demonstration.",
    )
    args = parser.parse_args()

    coach = PullRequestReviewCoach()
    if args.fixture:
        payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        review = coach.review_payload(payload["pr"], payload["files"], use_ai=not args.no_ai)
        result_data = review.to_dict()
    else:
        result = coach.execute({"pr_url": args.pr_url, "use_ai": not args.no_ai})
        if not result.success:
            print(json.dumps({"error": result.error}, indent=2))
            return 1
        result_data = result.data

    print(json.dumps(result_data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
