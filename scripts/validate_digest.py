"""Validate the digest artifact(s) produced by the Claude run.

Phase B: lenient — just confirms `output/digest.md` exists, is non-empty,
and is under Slack's hard text-field truncation point. Phase D/E tighten
this with Block Kit constraints and structural checks on `digest.json`.
"""

from __future__ import annotations

import pathlib
import sys


SLACK_TEXT_HARD_LIMIT = 40000  # Slack truncates `text` field around here.


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_digest.py <path-to-digest.md>", file=sys.stderr)
        return 2
    path = pathlib.Path(argv[1])
    if not path.exists():
        print(f"missing: {path}", file=sys.stderr)
        return 1
    body = path.read_text()
    if not body.strip():
        print(f"empty: {path}", file=sys.stderr)
        return 1
    if len(body) > SLACK_TEXT_HARD_LIMIT:
        print(
            f"too long: {len(body)} chars > Slack limit {SLACK_TEXT_HARD_LIMIT}",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {path} ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
