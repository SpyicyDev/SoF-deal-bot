"""Post the digest to Slack via incoming webhook.

Reads `output/digest.json` and POSTs the `main` payload (Block Kit). The
`deals[]` array is reserved for Phase G threaded-replies migration; this
script ignores it.

Falls back to a plain-text post built from `output/digest.md` if
`digest.json` is missing or malformed (defense in depth — validator
should have caught it earlier).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request


DIGEST_JSON = pathlib.Path("output/digest.json")
DIGEST_MD = pathlib.Path("output/digest.md")
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


def post_block_kit(webhook_url: str) -> bool:
    if not DIGEST_JSON.exists():
        return False
    try:
        payload = json.loads(DIGEST_JSON.read_text())
    except json.JSONDecodeError as exc:
        print(f"warning: digest.json invalid JSON ({exc}); falling back to text", file=sys.stderr)
        return False
    main_obj = payload.get("main") if isinstance(payload, dict) else None
    blocks = main_obj.get("blocks") if isinstance(main_obj, dict) else None
    if not blocks:
        print("warning: digest.json has no main.blocks; falling back to text", file=sys.stderr)
        return False

    fallback_text = "M&A Daily digest"
    for block in blocks:
        if block.get("type") == "header":
            fallback_text = block.get("text", {}).get("text", fallback_text)
            break

    post(webhook_url, {"text": fallback_text, "blocks": blocks})
    print(f"Posted Block Kit message ({len(blocks)} blocks).")
    return True


def post_text_fallback(webhook_url: str) -> None:
    if not DIGEST_MD.exists():
        raise RuntimeError(f"missing both {DIGEST_JSON} and {DIGEST_MD}; nothing to post")
    text = DIGEST_MD.read_text()
    if len(text) > SLACK_TEXT_HARD_LIMIT:
        text = text[: SLACK_TEXT_HARD_LIMIT - 200] + "\n\n_…digest truncated; see archive._"
    post(webhook_url, {"text": text, "mrkdwn": True})
    print(f"Posted plain-text fallback ({len(text)} chars).")


def main() -> int:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set", file=sys.stderr)
        return 1

    if post_block_kit(webhook_url):
        return 0
    post_text_fallback(webhook_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
