"""Open a GitHub issue describing a failed digest run.

Invoked from the workflow's `if: failure()` step. Uses the standard
GITHUB_TOKEN with `issues: write` permission (must be granted at the
workflow level).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


GITHUB_API = "https://api.github.com"


def gh_post(path: str, token: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{GITHUB_API}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "sof-deal-bot",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GH_TOKEN / GITHUB_TOKEN not set", file=sys.stderr)
        return 1

    repo = os.environ["GITHUB_REPOSITORY"]
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ["GITHUB_RUN_ID"]
    run_url = f"{server}/{repo}/actions/runs/{run_id}"
    today = os.environ.get("DIGEST_DATE", "")
    sha = os.environ.get("GITHUB_SHA", "")[:7]

    title_date = today or "(date unknown)"
    title = f"Daily digest failed {title_date}"
    body_lines = [
        "The scheduled M&A digest run failed.",
        "",
        f"- Run: {run_url}",
        f"- Commit: `{sha}`",
        f"- Workflow: `{os.environ.get('GITHUB_WORKFLOW', '')}`",
        f"- Triggered by: `{os.environ.get('GITHUB_EVENT_NAME', '')}`",
        "",
        "Open the run link above for full logs.",
    ]

    digest_excerpt_path = os.path.join("output", "digest.md")
    if os.path.exists(digest_excerpt_path):
        try:
            excerpt = open(digest_excerpt_path, encoding="utf-8").read()[:2000]
            if excerpt.strip():
                body_lines += [
                    "",
                    "<details><summary>Digest excerpt (first 2000 chars)</summary>",
                    "",
                    "```",
                    excerpt,
                    "```",
                    "",
                    "</details>",
                ]
        except OSError:
            pass

    body = "\n".join(body_lines)

    issue = gh_post(
        f"/repos/{repo}/issues",
        token,
        {"title": title, "body": body, "labels": ["digest-failure"]},
    )
    print(f"Opened issue #{issue.get('number')}: {issue.get('html_url')}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        sys.exit(1)
