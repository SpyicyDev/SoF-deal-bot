"""Render `prompts/daily_news.md` with run-context substitutions.

Reads `state/last_run.json` and `state/posted_urls.json` if present (empty
defaults otherwise) and substitutes `{{TODAY}}`, `{{LAST_RUN_TS}}`,
`{{MODE}}`, `{{POSTED_URLS_JSON}}` into the template. Writes the rendered
prompt to `output/prompt.md`.

Also exports the resolved values to `$GITHUB_OUTPUT` so later workflow
steps can reference them.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "prompts" / "daily_news.md"
LAST_RUN_PATH = REPO_ROOT / "state" / "last_run.json"
POSTED_URLS_PATH = REPO_ROOT / "state" / "posted_urls.json"
OUTPUT_DIR = REPO_ROOT / "output"
OUTPUT_PROMPT = OUTPUT_DIR / "prompt.md"


def load_json(path: pathlib.Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def resolve_mode(today: dt.date, override: str | None) -> str:
    if override:
        return override
    if today.weekday() == 0:  # Monday
        return "weekend_wrap"
    return "daily"


def emit_github_output(**kwargs: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        for key, value in kwargs.items():
            f.write(f"{key}={value}\n")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today = dt.datetime.now(dt.timezone.utc).date()
    today_str = today.isoformat()

    mode_override = os.environ.get("MODE_INPUT") or None
    mode = resolve_mode(today, mode_override)

    last_run = load_json(LAST_RUN_PATH, {})
    last_run_ts = last_run.get("last_run_utc", "") if isinstance(last_run, dict) else ""

    posted = load_json(POSTED_URLS_PATH, {"entries": []})
    entries = posted.get("entries", []) if isinstance(posted, dict) else []
    posted_json = json.dumps(entries, indent=2)

    template = TEMPLATE.read_text()
    rendered = (
        template
        .replace("{{TODAY}}", today_str)
        .replace("{{MODE}}", mode)
        .replace("{{LAST_RUN_TS}}", last_run_ts)
        .replace("{{POSTED_URLS_JSON}}", posted_json)
    )
    OUTPUT_PROMPT.write_text(rendered)

    emit_github_output(today=today_str, mode=mode, last_run_ts=last_run_ts)
    print(f"Rendered prompt → {OUTPUT_PROMPT} (mode={mode}, last_run_ts={last_run_ts!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
