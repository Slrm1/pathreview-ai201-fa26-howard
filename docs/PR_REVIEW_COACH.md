# AI PR Review Coach — Extra Credit Extension

The PR Review Coach extends PathReview with focused feedback for a public GitHub pull request.
It accepts a canonical PR URL, retrieves the PR description and file patches, and produces a
structured review with a summary, risks, test gaps, and next steps.

## Why this is an AI engineering project

- It builds bounded model context from an external data source.
- It treats repository content as untrusted and tells the model not to follow instructions in it.
- It limits the number of files and diff characters before any model call.
- It requests structured JSON and normalizes the result.
- It includes a deterministic fallback so the feature remains testable without an API key.
- It mocks network calls in unit tests instead of depending on GitHub or an LLM during CI.

## Run the reproducible offline demonstration

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
make pr-review-demo
```

The included fixture mirrors the shape of PathReview PR #78, so this command works without a
GitHub token, network connection, or paid LLM key.

![PR Review Coach terminal demonstration](images/pr-review-coach-demo.png)

## Review a live public pull request

```bash
.venv/bin/python scripts/pr_review_coach.py \
  https://github.com/codepath/pathreview-ai201-fa26-howard/pull/78 --no-ai
```

Remove `--no-ai` to use the configured model. Set `OPENROUTER_API_KEY` (recommended for this
project) or `OPENAI_API_KEY`, then set `LLM_PROVIDER` to a non-`mock` value.

Optional: set `GITHUB_TOKEN` to increase the GitHub API rate limit. Never commit any token.

## Example output

```json
{
  "summary": "fix(api): use configured Redis URL in health check changes 3 file(s) with +67/-8 lines.",
  "risks": [
    "Dependency files changed; verify version compatibility and security impact."
  ],
  "test_gaps": [
    "Confirm tests cover both the successful path and at least one failure path."
  ],
  "next_steps": [
    "Run the repository's formatter, type checker, and focused test suite.",
    "Verify the PR description explains the problem, solution, and testing evidence.",
    "Ask a reviewer to inspect the highest-risk changed file before merging."
  ],
  "files_reviewed": 3,
  "diff_truncated": false,
  "analysis_mode": "deterministic fallback"
}
```

## Tests and quality checks

```bash
.venv/bin/pytest tests/unit/test_pr_review_coach.py -q
.venv/bin/ruff check agent/tools/pr_review_coach.py scripts/pr_review_coach.py \
  tests/unit/test_pr_review_coach.py
.venv/bin/black --check agent/tools/pr_review_coach.py scripts/pr_review_coach.py \
  tests/unit/test_pr_review_coach.py
.venv/bin/mypy agent/tools/pr_review_coach.py
```

The focused suite covers URL validation, structured output, missing-test detection, context
truncation, and safe handling of inaccessible PRs.
