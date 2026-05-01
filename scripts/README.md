# Auto-resolver scripts

## Files

- `auto-resolve-issues.sh` — bash orchestrator. Selects up to 3 oldest open issues, branches off `main`, invokes `claude -p` per issue, opens a PR or comments on failure.
- `issue-resolver-prompt.md` — prompt template rendered via `envsubst` and piped to the Claude session. Uses the superpowers workflow (see `docs/superpowers/specs/2026-04-30-cron-issue-resolver-superpowers-amendment.md`).

## Crontab entry (host-local — not deployed by this repo)

Installed manually on the host via `crontab -e` for the user that owns the repo. Current line:

```
0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1
```

Fires daily at 02:00 in the host's local timezone. Confirm the timezone with `timedatectl` before relying on the schedule.

## Logs

- `logs/cron-issues-YYYY-MM-DD.log` — one per run, 30-day retention.
- `logs/cron-issue-NNN-YYYY-MM-DD.stderr` — per-issue stderr, 30-day retention.
- `logs/cron-stdout.log` — cumulative stdout/stderr from cron itself; rotate manually if it grows.

## Manual run

For ad-hoc debugging:

```bash
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh   # dry-run, no Claude invocation
/srv/auto-skedway/scripts/auto-resolve-issues.sh             # full run
```
