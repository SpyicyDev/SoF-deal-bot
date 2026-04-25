"""Post the digest to Slack via incoming webhook.

Phase B: reads `output/digest.md` (Slack mrkdwn) and posts it as a single
`text`-field message. Phase E swaps this for a Block Kit payload.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request


DIGEST_PATH = pathlib.Path("output/digest.md")
SLACK_TEXT_HARD_LIMIT = 40000


def post(webhook_url: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.status
        text = resp.read().decode("utf-8", errors="replace")
    if status != 200 or text.strip() != "ok":
        raise RuntimeError(f"Slack webhook returned status={status} body={text!r}")


def main() -> int:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set", file=sys.stderr)
        return 1
    if not DIGEST_PATH.exists():
        print(f"missing digest: {DIGEST_PATH}", file=sys.stderr)
        return 1

    text = DIGEST_PATH.read_text()
    if len(text) > SLACK_TEXT_HARD_LIMIT:
        text = text[:SLACK_TEXT_HARD_LIMIT - 200] + "\n\n_…digest truncated; see archive._"

    post(webhook_url, {"text": text, "mrkdwn": True})
    print(f"Posted digest to Slack ({len(text)} chars).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
