# Auto issue resolver

A nightly cron job that picks up to 3 of the oldest open GitHub issues on this repo, plans a fix with Claude Opus using the superpowers workflow, dispatches Sonnet 4.6 subagents in parallel for implementation, runs an Opus code review (up to 2 iterations), and opens one Pull Request per resolved issue. Failures comment on the issue with a short reason. **No auto-merge** — the user reviews and merges PRs manually.

## Files

| File | Role |
|---|---|
| `auto-resolve-issues.sh` | Bash orchestrator (~80 LOC). Drives `gh`, `git`, and `claude -p` for each issue. |
| `issue-resolver-prompt.md` | Prompt template rendered via `envsubst` and piped to the Claude session. |

## How a run unfolds

```
cron (0 2 * * *)
   │
   ▼
auto-resolve-issues.sh
   │  1. Pre-flight: log rotation, checkout main, ff-pull, clean working tree check
   │  2. Fetch up to 3 oldest open issues via `gh issue list ... sort:created-asc`
   │  3. For each issue:
   │       a. Skip if branch auto/issue-NNN exists locally OR remotely
   │       b. Create branch  auto/issue-NNN  off main
   │       c. Render prompt template with envsubst, invoke claude -p (30-min timeout)
   │       d. Parse last-line JSON sentinel from claude's stdout
   │       e. Verify a commit was made (HEAD != main)
   │       f. Success → push branch, open PR, comment on issue
   │          Failure → comment on issue with reason, delete local branch
   │  4. Write summary line: "N PR(s) opened, M failure(s), K skipped"
```

## Per-issue Claude workflow (the superpowers loop)

The prompt template instructs the per-issue Claude session to follow this workflow:

1. **Understand the request.** Read the issue title, body, and all comments. Prefer recent maintainer comments over the original body when in conflict.
2. **Decide whether to brainstorm.** Bug with clear repro → skip. Feature, ambiguous scope, or open-ended change → invoke `superpowers:brainstorming` headlessly (answer own clarifying questions, save spec under `docs/superpowers/specs/`).
3. **Plan.** Invoke `superpowers:writing-plans`. Save plan under `docs/superpowers/plans/`.
4. **Implement step by step.** Per-step decision: TDD required for behavior changes, skipped for docs/config. Independent steps dispatched in parallel as `Agent(subagent_type="general-purpose", model="sonnet", ...)`.
5. **Code review.** Invoke `superpowers:requesting-code-review`. Reviewer is `Agent(subagent_type="superpowers:code-reviewer", model="opus", ...)`. Up to 2 iterations:
   - Iteration 1 reproved → dispatch a Sonnet subagent to apply fixes, re-run reviewer.
   - Iteration 2 reproved → terminate with `{"status":"error","reason":"code review failed after 2 iterations: ..."}` and run cleanup.
6. **Commit on the per-issue branch.** Single commit `git commit -m "fix: <summary> (closes #N)"`. Do NOT push, do NOT open PR, do NOT comment — those are the orchestrator's job.
7. **Print the JSON sentinel** as the final stdout line.

### JSON sentinel contract

The very last line of Claude's stdout MUST be one of:

```json
{"status":"ok","summary":"<one-sentence description>"}
{"status":"error","reason":"<short reason>"}
```

On `error`, Claude must NOT commit and must leave the working tree clean (`git clean -fd docs/superpowers/specs docs/superpowers/plans && git checkout -- .` if it had created spec/plan artifacts).

## Bash decision logic per issue

```
exit=$?
last_json=$(tail -n 1 stdout)
status=$(echo "$last_json" | jq -r '.status // "missing"')

if   [[ $exit == 124 ]]; then          fail "timed out after 30m"
elif [[ $exit -ne 0 ]];   then          fail "claude exited $exit"
elif [[ "$status" == "missing" ]]; then fail "no JSON sentinel"
elif [[ "$status" != "ok" ]]; then      fail "$reason_from_json"
elif [[ HEAD == main ]];   then         fail "claude reported ok but no commit"
else
  git push -u origin "$BRANCH_NAME"
  pr_url=$(gh pr create --base main --head "$BRANCH_NAME" ...)
  gh issue comment "$N" --body "Auto-resolver opened $pr_url"
fi

# fail() = gh issue comment + cleanup local branch
```

## Pre-flight checks

Run in order at the start of every invocation. Any failure aborts the whole run before touching any issue:

1. `cd $WORKDIR`
2. `git checkout main` — must succeed
3. `git pull --ff-only origin main` — must succeed (non-FF aborts)
4. `git status --porcelain` — must be empty (dirty tree aborts to protect in-progress work)

Per-issue pre-flight:

- **Branch already exists** (local or remote) → skip the issue and log `branch exists, skipping #N`. Avoids conflict from a previous stalled run.

## Error handling matrix

| Failure | Detection | Action |
|---|---|---|
| `gh issue list` non-zero | exit code | Abort whole run (no issue comments posted) |
| Pre-flight fails (dirty tree, non-FF, etc.) | exit code | Abort whole run |
| `claude -p` non-zero (not 124) | exit code | Comment on issue with `(see <stderr file>)`; cleanup branch |
| `claude -p` times out (exit 124) | exit code | Comment "timed out after 30m"; cleanup branch |
| Claude returns `status=error` | last-line JSON | Comment with `reason` from JSON; cleanup branch |
| Claude returns `ok` but no commit | `HEAD == main` | Treat as error: comment + cleanup |
| `git push` non-zero | exit code | Comment with stderr tail; cleanup local branch |
| `gh pr create` non-zero | exit code | Comment "PR creation failed, branch pushed as `<name>`"; **leave remote branch** for manual PR |
| `gh issue comment` (final) fails | exit code | Log warning only; PR was already created |

## Logging

| File | Content | Retention |
|---|---|---|
| `logs/cron-issues-YYYY-MM-DD.log` | One per run. Plain text, line-prefixed `[YYYY-MM-DD HH:MM:SS]`. | 30 days |
| `logs/cron-issue-NNN-YYYY-MM-DD.stderr` | Full stderr from `claude -p` for issue NNN. Consulted only on failure. | 30 days |
| `logs/cron-stdout.log` | Cumulative stdout/stderr from cron itself (append-only). | Rotate manually if it grows |

Log rotation runs at the top of each invocation:

```bash
find /srv/auto-skedway/logs -name 'cron-issue*' -mtime +30 -delete
```

### Sample log

```
[2026-04-30 02:00:01] === Run started (DRY_RUN=0) ===
[2026-04-30 02:00:01] Pre-flight ok (on main, clean, up to date)
[2026-04-30 02:00:02] Fetched 3 open issue(s) to process
[2026-04-30 02:00:02] --- Issue #12: "Fix login redirect loop" ---
[2026-04-30 02:00:02] Branch created: auto/issue-12
[2026-04-30 02:00:02] Invoking claude (model=claude-opus-4-7, timeout=30m)
[2026-04-30 02:14:33] Claude exit=0, status=ok, summary="Fixed redirect by checking auth state in middleware"
[2026-04-30 02:14:35] Pushed auto/issue-12, opened https://github.com/.../pull/45, commented on issue #12
[2026-04-30 02:47:12] === Run finished: 2 PR(s) opened, 1 failure(s), 0 skipped ===
```

## Configuration

Variables at the top of `auto-resolve-issues.sh`:

| Variable | Default | Description |
|---|---|---|
| `WORKDIR` | `/srv/auto-skedway` | Repo root |
| `REPO` | `cassioerodrigues/auto-skedway` | GitHub `owner/repo` |
| `MAX_ISSUES` | `3` | Max issues processed per run |
| `MODEL_PLAN` | `claude-opus-4-7` | Claude model for the per-issue session |
| `CLAUDE_TIMEOUT` | `30m` | Hard timeout on `claude -p` (uses GNU `timeout`) |
| `LOG_RETENTION_DAYS` | `30` | Log rotation threshold |
| `DRY_RUN` | `0` | If `1`, runs everything except `claude -p`, push, PR, and issue comments |
| `CLAUDE_BIN` | `/root/.local/bin/claude` | Absolute path to `claude` CLI |
| `GH_BIN` | `/usr/bin/gh` | Absolute path to GitHub CLI |

### Prompt template variables

`issue-resolver-prompt.md` is rendered through `envsubst` with this allowlist (set per-issue by the orchestrator):

- `${ISSUE_NUMBER}`
- `${ISSUE_TITLE}`
- `${ISSUE_BODY}`
- `${ISSUE_COMMENTS_FORMATTED}` — chronological, one `--- @author em <ISO> ---` block per comment
- `${BRANCH_NAME}` — always `auto/issue-${ISSUE_NUMBER}`

Other `${...}` literals in the template are escaped or kept verbatim (envsubst with allowlist does not expand variable values recursively).

## Crontab entry (host-local — not deployed by this repo)

Installed manually on the host:

```
0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1
```

Fires daily at 02:00 in the host's local timezone. The host on `/srv/auto-skedway` runs `America/Sao_Paulo`, so this is 02:00 BRT. Confirm with `timedatectl` if you redeploy elsewhere.

To inspect / edit:

```bash
crontab -l
crontab -e
```

## Manual run

```bash
# Dry-run: pre-flight, issue selection, branching, but NO claude / push / PR / issue comments.
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh

# Full run (writes to GitHub):
/srv/auto-skedway/scripts/auto-resolve-issues.sh
```

The script is also `source`-able for testing internal helpers — it has a `BASH_SOURCE` guard so `main` only runs when executed directly. Useful for unit-testing `parse_claude_result`, `branch_exists`, etc.

## Authentication and binaries

The cron environment is minimal — the script uses absolute paths for both CLIs:

- `claude` — uses persisted credentials at `/root/.claude/.credentials.json`. Required flag: `--dangerously-skip-permissions` (no human to approve tool calls in a headless session).
- `gh` — uses the token at `/root/.config/gh/hosts.yml`. Needs the `repo` scope.

If either credential expires, the script will fail every invocation until refreshed. Failures are visible in `cron-stdout.log` and the per-day `cron-issues-*.log`.

## Out of scope (deferred)

- Retry of issues that failed previous nights (label manually if you want a retry)
- Stop-list label (e.g., `auto-skip`) — configure manually if needed
- Email/Slack notifications — GitHub PR list + log file is sufficient
- Auto-merge on green CI
- Metrics / monthly reports
