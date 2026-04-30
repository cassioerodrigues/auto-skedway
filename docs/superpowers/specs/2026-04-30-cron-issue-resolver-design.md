# Cron Issue Resolver — Design

**Date:** 2026-04-30
**Status:** Approved (pending implementation plan)
**Repo:** `cassioerodrigues/auto-skedway`
**Server:** `/srv/auto-skedway` (America/Sao_Paulo)

## Goal

Run a nightly job at 02:00 BRT that picks up to 3 open GitHub issues, plans a fix with Claude Opus, dispatches Claude Haiku subagents to do the work in parallel, then opens one Pull Request per issue. Failures are surfaced as comments on the issue.

The user reviews and merges PRs manually. No auto-merge.

## Architecture

```
cron (0 2 * * *)
   │
   ▼
scripts/auto-resolve-issues.sh
   │  1. Pre-flight: clean working tree, log rotation, fetch open issues
   │  2. For each of up to 3 oldest open issues:
   │       a. Create branch  auto/issue-NNN  off main
   │       b. Render prompt template, invoke `claude -p --model opus`
   │       c. Parse last-line JSON sentinel from Claude's stdout
   │       d. On success → push branch + open PR + comment on issue
   │          On failure → comment on issue + delete local branch
   │  3. Write per-day log; per-issue stderr files for forensics
```

### Components

| Component | Responsibility |
|---|---|
| `scripts/auto-resolve-issues.sh` | Orchestration: issue selection, git branching, claude invocation, push/PR/comment, logging. ~80 LOC bash. |
| `scripts/issue-resolver-prompt.md` | Prompt template injected via `envsubst`. Tells Claude how to plan, dispatch subagents, commit. |
| `logs/cron-issues-YYYY-MM-DD.log` | One log file per run (per day). Daily rotation deletes files older than 30 days. |
| `logs/cron-issue-NNN-YYYY-MM-DD.stderr` | Per-issue stderr from `claude -p`. Consulted only on failure. |
| `crontab` entry | `0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1` |

## Data flow

### Issue selection

```bash
gh issue list --repo cassioerodrigues/auto-skedway \
  --state open --limit 3 --json number,title \
  --search "sort:created-asc"
```

Oldest 3 open issues. No label filter.

### Per-issue context for Claude

```bash
gh issue view "$N" --json title,body,comments \
  --jq '{title, body, comments: [.comments[] | {author: .author.login, body: .body, createdAt: .createdAt}]}'
```

Comments are rendered into the prompt in chronological order:

```
--- @username em 2026-04-29T10:32:00Z ---
<comment body>
```

Prompt instruction: *"Comments may refine, contradict, or clarify the original body — when in conflict, prefer the most recent comment from the issue author or a maintainer."*

### Prompt template (`scripts/issue-resolver-prompt.md`)

Uses `envsubst` substitution for: `$ISSUE_NUMBER`, `$ISSUE_TITLE`, `$ISSUE_BODY`, `$ISSUE_COMMENTS_FORMATTED`, `$BRANCH_NAME`.

Template instructs Claude to:

1. Read the issue title, body, and comments. Explore relevant code with Read/Grep/Bash.
2. Call `Agent(subagent_type="Plan", prompt="<context + issue body + comments>")` to produce a structured plan.
3. For independent steps in the plan, dispatch in parallel:
   `Agent(subagent_type="general-purpose", model="haiku", prompt="<step>")`
4. Validate results, then `git add -A && git commit -m "fix: <summary> (closes #$ISSUE_NUMBER)"`.
5. **Do NOT push or open the PR** — that is the bash script's job.
6. Print as the **final stdout line** a JSON sentinel:
   - Success: `{"status":"ok","summary":"<one-line summary>"}`
   - Failure: `{"status":"error","reason":"<short reason>"}`

The `closes #N` trailer makes GitHub auto-close the issue when the PR is merged.

### Claude invocation

```bash
timeout 30m claude -p \
  --model claude-opus-4-7 \
  --add-dir /srv/auto-skedway \
  --output-format json \
  --dangerously-skip-permissions \
  < <(envsubst < scripts/issue-resolver-prompt.md)
```

- `--dangerously-skip-permissions` is required for headless cron (no human to approve tool calls).
- `--output-format json` returns structured metadata; the last-line JSON sentinel from the assistant message is the authoritative outcome signal.
- 30-minute hard timeout — exceeded sessions are killed and the issue is commented as "timed out".

### Bash decision logic per issue

```
exit=$?
last_json=$(tail -n 1 stdout.txt)
status=$(echo "$last_json" | jq -r '.status // "missing"')

if [[ $exit -ne 0 ]]; then
    fail "claude exited $exit"
elif [[ "$status" != "ok" ]]; then
    reason=$(echo "$last_json" | jq -r '.reason // "no reason given"')
    fail "$reason"
elif [[ "$(git rev-parse HEAD)" == "$(git rev-parse main)" ]]; then
    fail "claude reported ok but no commit was made"
else
    git push -u origin "$BRANCH_NAME"
    pr_url=$(gh pr create --title "..." --body "..." --base main)
    gh issue comment "$N" --body "Auto-resolver opened $pr_url"
fi

# fail() = gh issue comment with reason + git checkout main + git branch -D $BRANCH_NAME
```

## Error handling

| Failure point | Detection | Action |
|---|---|---|
| `gh issue list` non-zero | exit code | Log + abort whole run (no comments posted) |
| `claude -p` non-zero | exit code | `gh issue comment` with stderr tail + branch cleanup |
| Claude returns `status=error` | last-line JSON | `gh issue comment` with reason + branch cleanup |
| Claude returns `ok` but no commit | `git rev-parse HEAD == main` | Treat as error: comment + cleanup |
| `git push` non-zero | exit code | `gh issue comment` with stderr + cleanup local branch |
| `gh pr create` non-zero | exit code | `gh issue comment` "PR creation failed, branch pushed as `<name>`" — leave remote branch for manual PR |
| `claude -p` exceeds 30 min | `timeout` returns 124 | `gh issue comment` "timed out after 30min" + cleanup |

### Pre-flight protections

Executed in order at the start of each run:

1. `cd $WORKDIR`
2. `git checkout main` — if this fails (e.g., uncommitted changes block checkout), abort whole run.
3. `git pull --ff-only origin main` — if non-fast-forward, abort whole run.
4. `git status --porcelain` — if non-empty after step 3, abort with log "dirty working tree, aborting". Protects user's in-progress work.

Per-issue pre-flight:

- **Branch exists:** before creating `auto/issue-N`, check both `git rev-parse --verify auto/issue-N` (local) and `git ls-remote --heads origin auto/issue-N` (remote). If either exists, skip that issue and log "branch exists, skipping #N". Avoids conflicts from a previous stalled run.

### Out of scope (deferred)

- Retry of issues that failed previous nights (user adds label manually if needed)
- Stop-list label (e.g., `auto-skip`) — user can configure manually for now
- Email/Slack notifications — GitHub PR list + log file is sufficient
- Auto-merge on green CI
- Metrics / monthly reports

## Logging

### Per-run log: `logs/cron-issues-YYYY-MM-DD.log`

Plain text, line-prefixed with `[YYYY-MM-DD HH:MM:SS]`. Sample:

```
[2026-04-30 02:00:01] === Run started ===
[2026-04-30 02:00:01] Working tree clean: ok
[2026-04-30 02:00:02] Fetched 7 open issues, processing 3 oldest: #12 #15 #18
[2026-04-30 02:00:02] --- Issue #12: "Fix login redirect loop" ---
[2026-04-30 02:00:02] Branch created: auto/issue-12
[2026-04-30 02:00:02] Invoking claude (model=opus, timeout=30m)
[2026-04-30 02:14:33] Claude exit=0, status=ok, summary="Fixed redirect by checking auth state in middleware"
[2026-04-30 02:14:34] Pushed auto/issue-12, opened PR #45
[2026-04-30 02:14:35] Commented on issue #12: "PR #45 opened"
[2026-04-30 02:14:35] --- Issue #15: "..." ---
...
[2026-04-30 02:47:12] === Run finished: 2 PRs opened, 1 issue commented (failed) ===
```

### Per-issue stderr: `logs/cron-issue-NNN-YYYY-MM-DD.stderr`

Full stderr from `claude -p` for forensics on failures. Same 30-day retention.

### Log rotation

At the top of each run:

```bash
find /srv/auto-skedway/logs -name 'cron-issue*' -mtime +30 -delete
```

## Configuration

Variables at the top of `auto-resolve-issues.sh`:

```bash
MAX_ISSUES=3
MODEL_PLAN="claude-opus-4-7"
CLAUDE_TIMEOUT="30m"
LOG_RETENTION_DAYS=30
DRY_RUN="${DRY_RUN:-0}"
REPO="cassioerodrigues/auto-skedway"
WORKDIR="/srv/auto-skedway"
```

`DRY_RUN=1` runs everything **up to** `claude -p` invocation, then logs what would have happened — used for first-run validation.

## Installation steps

1. Create `scripts/auto-resolve-issues.sh` and `scripts/issue-resolver-prompt.md`.
2. `chmod +x scripts/auto-resolve-issues.sh`.
3. Run once with `DRY_RUN=1 ./scripts/auto-resolve-issues.sh` to validate selection + branching + prompt rendering.
4. Run once without `DRY_RUN` against a single test issue to validate full end-to-end flow.
5. Add to root crontab:
   ```
   0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1
   ```

## Open assumptions to confirm during implementation

- `claude -p` headless authentication uses persisted credentials at `/root/.claude/.credentials.json` — verified present, but actual headless invocation should be smoke-tested before enabling cron.
- `gh` token at `/root/.config/gh/hosts.yml` has `repo` scope — confirmed.
- Cron `PATH` does not include `/root/.local/bin` by default — script must use absolute path to `claude` binary.
