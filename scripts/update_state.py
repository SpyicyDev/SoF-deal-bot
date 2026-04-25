"""Merge a run's posted URLs into state and rewrite last_run.json.

Reads `output/posted.json` (written by the writer agent) and merges new
entries into `state/posted_urls.json`, deduping by URL and pruning
entries older than 30 days. Then rewrites `state/last_run.json` from
scratch using the **start time** of this run (RUN_START_TS env var) so
that long-running jobs don't miss items published mid-run.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTED_OUT = REPO_ROOT / "output" / "posted.json"
STATE_URLS = REPO_ROOT / "state" / "posted_urls.json"
STATE_LAST_RUN = REPO_ROOT / "state" / "last_run.json"

TTL_DAYS = 30


def parse_iso8601(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json(path: pathlib.Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=TTL_DAYS)

    posted_run = load_json(POSTED_OUT, {"entries": []})
    new_entries = posted_run.get("entries", []) if isinstance(posted_run, dict) else []

    state = load_json(STATE_URLS, {"entries": []})
    existing = state.get("entries", []) if isinstance(state, dict) else []

    by_url: dict[str, dict] = {}
    for entry in existing:
        url = entry.get("url")
        if not url:
            continue
        first_seen = parse_iso8601(entry.get("first_seen", ""))
        if first_seen and first_seen < cutoff:
            continue
        by_url[url] = entry

    added = 0
    for entry in new_entries:
        url = entry.get("url")
        if not url:
            continue
        if url in by_url:
            continue
        by_url[url] = {
            "url": url,
            "first_seen": entry.get("first_seen") or now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "headline": entry.get("headline", ""),
            "deal_key": entry.get("deal_key", ""),
        }
        added += 1

    merged = {"entries": list(by_url.values())}
    STATE_URLS.write_text(json.dumps(merged, indent=2) + "\n")

    run_start = os.environ.get("RUN_START_TS") or now.isoformat(timespec="seconds").replace("+00:00", "Z")
    last_run = {
        "last_run_utc": run_start,
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "mode": os.environ.get("RUN_MODE", "daily"),
        "status": "success",
    }
    STATE_LAST_RUN.write_text(json.dumps(last_run, indent=2) + "\n")

    print(
        f"State updated: +{added} new, {len(merged['entries'])} total "
        f"(pruned to last {TTL_DAYS}d). last_run_utc={run_start}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
