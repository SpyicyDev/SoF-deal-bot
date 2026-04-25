"""Post the digest to Slack via incoming webhook.

Phase A: posts a hard-coded string. Later phases consume output/digest.json
for Block Kit payloads.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


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

    payload = {"text": "Hello SoF — daily digest scaffolding is wired up."}
    post(webhook_url, payload)
    print("Posted to Slack.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
