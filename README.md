# SoF Deal Bot

Daily M&A deal digest for the Scholars of Finance chapter, posted to Slack.

Runs at **7am US/Eastern** each weekday (Mon–Fri). Mondays automatically use a "weekend wrap" mode that covers from Friday 5pm ET through Sunday end-of-day. Uses [`anthropics/claude-code-base-action`](https://github.com/anthropics/claude-code-base-action) to research recent deal activity via `WebSearch` + `WebFetch`, drafts a sectored digest, has a reviewer subagent critique it, optionally revises once, then posts to a Slack channel via incoming webhook (Block Kit single-message format). Each run's digest is archived to `archive/YYYY-MM-DD.md` and posted URLs are tracked in `state/posted_urls.json` (rolling 30 days) for dedup on future runs.

## Repo secrets required

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Auth for `claude-code-base-action`. |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for the target channel. |

`GITHUB_TOKEN` is auto-provided by Actions. Ensure the repo's default workflow permissions allow `contents: write` and `issues: write` (Settings → Actions → General → Workflow permissions). The workflow declares these explicitly but org-level policy can still block.

### Slack incoming webhook setup

1. Slack → workspace settings → **Apps** → search "Incoming Webhooks" → **Add to Slack**.
2. Pick the target channel (e.g. `#sof-ma-digest`).
3. Copy the webhook URL (`https://hooks.slack.com/services/T…/B…/…`).
4. In the GitHub repo → Settings → Secrets and variables → Actions → **New repository secret** named `SLACK_WEBHOOK_URL`.

A future migration to threaded per-deal replies (Phase G) needs a Slack bot token, which requires workspace-admin install; the webhook path is the supported config today.

## Manual dispatch

Actions tab → "SoF Daily M&A Digest" → **Run workflow**. Inputs:

- `dry_run` _(default false)_ — when true, the digest renders to the job summary and the workflow skips Slack post + archive + commit. Use this to preview prompt changes safely.
- `mode` _(default `auto`)_ — `auto` resolves to `weekend_wrap` on Mondays and `daily` otherwise. Force a specific mode for backfills/testing.

## Layout

```
.github/workflows/daily-digest.yml   # scheduled + dispatch workflow (gate job + digest job)
prompts/
  daily_news.md                      # writer prompt template (placeholders rendered each run)
  reviewer.md                        # reviewer-subagent prompt body
scripts/
  render_prompt.py                   # substitute {{TODAY}}, {{LAST_RUN_TS}}, {{POSTED_URLS_JSON}}, {{MODE}}, {{ARCHIVE_URL}}
  validate_digest.py                 # enforce Block Kit limits + size checks
  post_to_slack.py                   # POST output/digest.json main.blocks via webhook
  update_state.py                    # merge new URLs into 30-day index; rewrite last_run.json
  open_failure_issue.py              # open a GitHub issue on workflow failure
  dst_gate.py                        # gate job: pass only at 7am ET (drops the off-DST cron)
state/
  last_run.json                      # { last_run_utc, run_id, mode, status }
  posted_urls.json                   # { entries: [{url, first_seen, headline, deal_key}] }
archive/                              # YYYY-MM-DD.md per run, committed by workflow
output/                               # gitignored scratch dir
```

## Local testing with [`act`](https://github.com/nektos/act)

The repo ships with an `.actrc`, `.secrets.example`, and event payloads under `.act/` so you can run the workflow locally in Docker without dispatching it from GitHub.

```bash
# 1. Copy the secrets template and fill in real values.
cp .secrets.example .secrets

# 2. Run the digest job in dry-run mode (no Slack post, no commit).
act workflow_dispatch \
  -W .github/workflows/daily-digest.yml \
  -e .act/event-dry-run.json \
  --secret-file .secrets \
  -j digest

# 3. Just the gate job (verifies DST gate / dispatch bypass in isolation).
act workflow_dispatch \
  -W .github/workflows/daily-digest.yml \
  -e .act/event-dry-run.json \
  --secret-file .secrets \
  -j gate
```

For an end-to-end run that actually posts to Slack and commits state, use `.act/event-full.json`.

The included `.actrc` pins the medium `catthehacker/ubuntu:act-latest` image (~500MB). It has Python 3.12 + Node + curl preinstalled, which is why the workflow doesn't include `actions/setup-python` (system Python is sufficient on GitHub-hosted runners too — they ship Python 3.10+).

Note: act sets `GITHUB_REPOSITORY` from the remote URL rather than `owner/repo`. The render script defensively strips that down, but you can also override it explicitly: `--env GITHUB_REPOSITORY=spyicydev/sof-deal-bot`.

## Build phases (commit history)

Each phase is a runnable end-to-end version on top of the previous. Walk back through `git log` to inspect the foundation each layer was built on.

- **Phase A** — scaffolding (hello-world action + Slack post + failure issue).
- **Phase B** — real research with WebSearch/WebFetch, single-message mrkdwn post.
- **Phase C** — archive + dedup state + commit-back.
- **Phase D** — reviewer subagent + one-pass revision loop.
- **Phase E** — Block Kit single-message format with sector grouping + archive footer link.
- **Phase F** — dry-run input, mode override, DST-gated cron pair.
- **Phase G** _(deferred)_ — Slack bot token + threaded per-deal replies. Requires workspace-admin install. The writer already produces `digest.json["deals"]` so the migration is a poster swap.
