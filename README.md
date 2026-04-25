# SoF Deal Bot

Daily M&A deal digest for the Scholars of Finance chapter, posted to Slack.

Runs each weekday morning at 7am ET. Uses [`anthropics/claude-code-base-action`](https://github.com/anthropics/claude-code-base-action) to research recent deal activity, drafts a sectored digest, has a reviewer subagent critique it, then posts to a Slack channel via incoming webhook.

## Repo secrets required

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Auth for `claude-code-base-action`. |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for the target channel. |

`GITHUB_TOKEN` is auto-provided by Actions; ensure repo default workflow permissions allow `contents: write` and `issues: write`.

## Manual dispatch

Trigger from the Actions tab → "SoF Daily M&A Digest" → "Run workflow". Phase F adds a `dry_run` input that prints the digest to the job summary and skips the Slack post.

## Layout

```
.github/workflows/daily-digest.yml   # scheduled + dispatch workflow
prompts/                              # writer + reviewer prompt files
scripts/                              # Python helpers (Slack post, state update, failure issue, etc.)
state/                                # last_run.json + posted_urls.json (committed by workflow)
archive/                              # YYYY-MM-DD.md per run (committed by workflow)
output/                               # gitignored scratch dir for run artifacts
```

## Build phases

This project is built in phases (see commits). Each phase is a runnable end-to-end version on top of the previous.

- **Phase A** — scaffolding (hello-world action + Slack post + failure issue).
- **Phase B** — real research with WebSearch/WebFetch, single-message markdown post.
- **Phase C** — archive + dedup state + commit-back.
- **Phase D** — reviewer subagent + revision loop.
- **Phase E** — Block Kit single-message format.
- **Phase F** — dry-run, weekend-wrap, DST-gated cron pair.
- **Phase G** _(deferred)_ — Slack bot token + threaded replies (needs workspace admin install).
