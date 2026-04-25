"""Validate the digest artifacts produced by the Claude run.

Checks `output/digest.md` (size) and `output/digest.json` (Block Kit
shape: ≤50 blocks in main.blocks, section text ≤3000 chars, fields text
≤2000 chars, headers ≤150 chars, deals[] populated).

Exits non-zero on any violation so the workflow fails loudly before
posting a malformed message to Slack.
"""

from __future__ import annotations

import json
import pathlib
import sys


SLACK_TEXT_HARD_LIMIT = 40000
DIGEST_MD_SOFT_LIMIT = 35000
MAX_BLOCKS_PER_MESSAGE = 50
MAX_SECTION_TEXT = 3000
MAX_FIELD_TEXT = 2000
MAX_HEADER_TEXT = 150
MAX_FIELDS_PER_SECTION = 10


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def check_blocks(blocks: list[dict], where: str, errors: list[str]) -> None:
    if len(blocks) > MAX_BLOCKS_PER_MESSAGE:
        fail(
            f"{where}: {len(blocks)} blocks exceeds Slack limit {MAX_BLOCKS_PER_MESSAGE}",
            errors,
        )
    for i, block in enumerate(blocks):
        btype = block.get("type")
        if btype == "header":
            text = block.get("text", {})
            if text.get("type") != "plain_text":
                fail(f"{where}[{i}] header.text.type must be plain_text", errors)
            if len(text.get("text", "")) > MAX_HEADER_TEXT:
                fail(
                    f"{where}[{i}] header text > {MAX_HEADER_TEXT} chars: "
                    f"{len(text.get('text',''))}",
                    errors,
                )
        elif btype == "section":
            text = block.get("text")
            if text and len(text.get("text", "")) > MAX_SECTION_TEXT:
                fail(
                    f"{where}[{i}] section.text.text > {MAX_SECTION_TEXT} chars: "
                    f"{len(text['text'])}",
                    errors,
                )
            fields = block.get("fields", []) or []
            if len(fields) > MAX_FIELDS_PER_SECTION:
                fail(
                    f"{where}[{i}] section.fields has {len(fields)} > "
                    f"{MAX_FIELDS_PER_SECTION}",
                    errors,
                )
            for j, field in enumerate(fields):
                if len(field.get("text", "")) > MAX_FIELD_TEXT:
                    fail(
                        f"{where}[{i}].fields[{j}] text > {MAX_FIELD_TEXT} chars",
                        errors,
                    )
        elif btype in {"divider", "context"}:
            pass  # context elements have their own short limits; skip detailed check
        else:
            # Unknown block types aren't fatal; Slack will reject if invalid.
            pass


def main(argv: list[str]) -> int:
    md_path = pathlib.Path(argv[1] if len(argv) > 1 else "output/digest.md")
    json_path = pathlib.Path(argv[2] if len(argv) > 2 else "output/digest.json")

    errors: list[str] = []

    if not md_path.exists():
        fail(f"missing: {md_path}", errors)
    else:
        body = md_path.read_text()
        if not body.strip():
            fail(f"empty: {md_path}", errors)
        if len(body) > SLACK_TEXT_HARD_LIMIT:
            fail(
                f"{md_path}: {len(body)} chars > Slack hard limit {SLACK_TEXT_HARD_LIMIT}",
                errors,
            )
        elif len(body) > DIGEST_MD_SOFT_LIMIT:
            print(
                f"warning: {md_path} is {len(body)} chars (soft limit "
                f"{DIGEST_MD_SOFT_LIMIT})",
                file=sys.stderr,
            )

    if not json_path.exists():
        fail(f"missing: {json_path}", errors)
    else:
        try:
            payload = json.loads(json_path.read_text())
        except json.JSONDecodeError as exc:
            fail(f"{json_path}: invalid JSON ({exc})", errors)
            payload = None

        if isinstance(payload, dict):
            main_obj = payload.get("main", {})
            main_blocks = main_obj.get("blocks", []) if isinstance(main_obj, dict) else []
            if not main_blocks:
                fail(f"{json_path}: main.blocks missing or empty", errors)
            else:
                check_blocks(main_blocks, "main.blocks", errors)

            deals = payload.get("deals")
            if deals is None:
                fail(
                    f"{json_path}: deals[] missing (required for Phase G migration)",
                    errors,
                )
            elif not isinstance(deals, list):
                fail(f"{json_path}: deals must be an array", errors)
            else:
                for i, deal in enumerate(deals):
                    if not isinstance(deal, dict):
                        fail(f"{json_path}: deals[{i}] not an object", errors)
                        continue
                    if not deal.get("deal_key"):
                        fail(f"{json_path}: deals[{i}].deal_key missing", errors)
                    deal_blocks = deal.get("blocks", [])
                    if not isinstance(deal_blocks, list) or not deal_blocks:
                        fail(f"{json_path}: deals[{i}].blocks missing or empty", errors)
                        continue
                    check_blocks(deal_blocks, f"deals[{i}].blocks", errors)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"OK: {md_path} + {json_path} validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
