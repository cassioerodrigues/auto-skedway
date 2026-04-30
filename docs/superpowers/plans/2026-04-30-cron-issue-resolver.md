# Cron Issue Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a nightly cron job that picks up to 3 oldest open GitHub issues, plans a fix with Claude Opus, dispatches Haiku subagents in parallel, and opens one PR per resolved issue. Failures comment on the issue. No auto-merge.

**Architecture:** Bash orchestrator (`scripts/auto-resolve-issues.sh`) drives `gh` for GitHub I/O and `claude -p` for the planning+coding loop, using a templated prompt rendered via `envsubst`. Claude writes the JSON sentinel as its final stdout line; bash reads it to decide push/PR vs. fail-comment. Cron entry runs the script at 02:00 BRT daily.

**Tech Stack:** bash 5+, `gh` CLI, `git`, `claude` CLI (Claude Opus 4.7 + Haiku subagents), `envsubst`, `jq`, `shellcheck` (lint), GNU `coreutils` (`timeout`, `find`).

---

## Spec reference

`docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md`

## Pre-implementation note on output format

The spec mentioned `claude -p --output-format json`. After review, the implementation will use the **default text output** instead and rely on the last-line JSON sentinel printed by Claude. Reason: `--output-format json` wraps everything in one envelope, which complicates tail-line parsing without adding signal beyond what we already get from the sentinel. The bash script remains responsible for parsing only the last line of stdout.

## File layout to be created

```
/srv/auto-skedway/
├── scripts/
│   ├── auto-resolve-issues.sh        # main orchestrator (bash)
│   └── issue-resolver-prompt.md      # prompt template, envsubst-rendered
├── logs/
│   ├── cron-issues-YYYY-MM-DD.log    # one log per run
│   ├── cron-issue-NNN-YYYY-MM-DD.stderr  # per-issue stderr (forensics)
│   └── cron-stdout.log               # cron's own stdout/stderr capture
└── (crontab entry, configured manually)
```

---

## Task 1: Install shellcheck and create directory skeleton

**Files:**
- Create: `scripts/` directory
- Create: `scripts/auto-resolve-issues.sh` (skeleton only)
- Verify: `logs/` directory exists

- [ ] **Step 1: Install shellcheck**

```bash
apt update && apt install -y shellcheck
```

Expected: `shellcheck` available at `/usr/bin/shellcheck`. Verify with `which shellcheck`.

- [ ] **Step 2: Ensure directory layout**

```bash
mkdir -p /srv/auto-skedway/scripts
mkdir -p /srv/auto-skedway/logs
ls -la /srv/auto-skedway/scripts /srv/auto-skedway/logs
```

Expected: both directories exist and are empty (logs may have prior content; that's fine).

- [ ] **Step 3: Create skeleton script with config + logging helpers**

Create `/srv/auto-skedway/scripts/auto-resolve-issues.sh`:

```bash
#!/usr/bin/env bash
# Auto Issue Resolver — runs nightly via cron, opens 1 PR per open issue.
# See docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md
set -euo pipefail

# --- Configuration ---
WORKDIR="/srv/auto-skedway"
REPO="cassioerodrigues/auto-skedway"
MAX_ISSUES=3
MODEL_PLAN="claude-opus-4-7"
CLAUDE_TIMEOUT="30m"
LOG_RETENTION_DAYS=30
DRY_RUN="${DRY_RUN:-0}"
CLAUDE_BIN="/root/.local/bin/claude"
GH_BIN="/usr/bin/gh"

# --- Derived paths ---
DATE="$(date +%Y-%m-%d)"
LOG_FILE="$WORKDIR/logs/cron-issues-$DATE.log"
PROMPT_TEMPLATE="$WORKDIR/scripts/issue-resolver-prompt.md"

# --- Logging helpers ---
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

abort() {
  log "ABORT: $*"
  exit 1
}

# --- Log rotation ---
rotate_logs() {
  find "$WORKDIR/logs" -name 'cron-issue*' -mtime "+$LOG_RETENTION_DAYS" -delete 2>/dev/null || true
}

# --- Main entry point (filled in later tasks) ---
main() {
  cd "$WORKDIR"
  rotate_logs
  log "=== Run started (DRY_RUN=$DRY_RUN) ==="
  log "=== Run finished (skeleton only) ==="
}

main "$@"
```

- [ ] **Step 4: Make executable and lint**

```bash
chmod +x /srv/auto-skedway/scripts/auto-resolve-issues.sh
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: `shellcheck` produces no output (clean).

- [ ] **Step 5: Run skeleton end-to-end**

```bash
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh
cat /srv/auto-skedway/logs/cron-issues-$(date +%Y-%m-%d).log
```

Expected log lines:
```
[YYYY-MM-DD HH:MM:SS] === Run started (DRY_RUN=1) ===
[YYYY-MM-DD HH:MM:SS] === Run finished (skeleton only) ===
```

- [ ] **Step 6: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: skeleton orchestrator script for auto issue resolver"
```

---

## Task 2: Pre-flight checks

**Files:**
- Modify: `scripts/auto-resolve-issues.sh` (add pre-flight, replace skeleton main)

- [ ] **Step 1: Add pre-flight function**

Insert this function before `main()` in `auto-resolve-issues.sh`:

```bash
preflight() {
  cd "$WORKDIR"
  git checkout main >/dev/null 2>&1 || abort "git checkout main failed"
  git pull --ff-only origin main >/dev/null 2>&1 || abort "git pull --ff-only failed (non-FF or network error)"
  if [[ -n "$(git status --porcelain)" ]]; then
    abort "dirty working tree on main — refusing to run"
  fi
  log "Pre-flight ok (on main, clean, up to date)"
}
```

- [ ] **Step 2: Wire pre-flight into main**

Replace the `main()` body with:

```bash
main() {
  cd "$WORKDIR"
  rotate_logs
  log "=== Run started (DRY_RUN=$DRY_RUN) ==="
  preflight
  log "=== Run finished (pre-flight only) ==="
}
```

- [ ] **Step 3: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean.

- [ ] **Step 4: Verify clean tree behavior**

```bash
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh
tail -5 /srv/auto-skedway/logs/cron-issues-$(date +%Y-%m-%d).log
```

Expected: `Pre-flight ok` line, then `=== Run finished ===`.

- [ ] **Step 5: Verify dirty tree abort**

```bash
echo "test dirt" > /tmp/dirty-test.txt
ln -s /tmp/dirty-test.txt /srv/auto-skedway/dirty-test.txt
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh ; echo "exit=$?"
rm /srv/auto-skedway/dirty-test.txt /tmp/dirty-test.txt
```

Expected: log line `ABORT: dirty working tree on main — refusing to run`, exit code 1.

- [ ] **Step 6: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: pre-flight checks for clean working tree"
```

---

## Task 3: Prompt template file

**Files:**
- Create: `scripts/issue-resolver-prompt.md`

- [ ] **Step 1: Create prompt template**

Create `/srv/auto-skedway/scripts/issue-resolver-prompt.md`:

```markdown
You are running headlessly inside a cron-driven automation. There is no human to ask questions — make sensible decisions and proceed.

# Your job

Resolve GitHub issue #${ISSUE_NUMBER} from the repository `cassioerodrigues/auto-skedway`. The repository is checked out at `/srv/auto-skedway` and you are currently on branch `${BRANCH_NAME}` (forked from `main`). Your work must produce a single git commit on this branch that, when merged, closes the issue.

# Context

## Issue title

${ISSUE_TITLE}

## Issue body

${ISSUE_BODY}

## Discussion (chronological)

${ISSUE_COMMENTS_FORMATTED}

# How to work

1. **Understand the request.** Read the issue body and all comments. If a later comment from the issue author or a maintainer contradicts the original body, prefer the comment.

2. **Explore the code.** Use Read, Grep, and Bash freely to understand the relevant parts of the codebase.

3. **Plan with the Plan agent.** Invoke `Agent(subagent_type="Plan", prompt="<full context including issue body and what you have learned about the code>")` to produce a structured implementation plan. Read its output carefully.

4. **Dispatch Haiku subagents in parallel.** For independent steps in the plan, dispatch them concurrently in a single message:
   `Agent(subagent_type="general-purpose", model="haiku", prompt="<the specific step, with file paths and acceptance criteria>")`
   Sequential steps run one at a time. Each subagent should make focused, minimal changes.

5. **Validate.** After subagents return, read the changed files yourself to confirm the work matches the plan and the issue.

6. **Commit on the current branch.** Run:
   ```
   git add -A
   git commit -m "fix: <one-line summary> (closes #${ISSUE_NUMBER})"
   ```
   Do NOT push. Do NOT open the PR. The orchestrator script handles that.

7. **Print the JSON sentinel as the FINAL line of your output.** Nothing else after it.

# Output contract — REQUIRED

The very last line you print MUST be a single-line JSON object, no markdown, no surrounding text:

- On success:
  `{"status":"ok","summary":"<one-sentence description of the change you made>"}`

- On giving up (issue too ambiguous, missing info, scope explosion, repeated subagent failures):
  `{"status":"error","reason":"<short reason — what blocked you>"}`

If you give up, do NOT commit. Leave the working tree clean.

# Hard constraints

- Stay focused on the issue. Do not refactor, rename, or reorganize unrelated code.
- Do not add error handling, comments, or scaffolding the issue did not ask for.
- Do not push, open PRs, or comment on the issue. The orchestrator does those steps.
- The JSON sentinel must be the final line of stdout. No exceptions.
```

- [ ] **Step 2: Verify the template renders correctly with envsubst**

```bash
ISSUE_NUMBER=999 \
ISSUE_TITLE="Test title with \$dollar signs" \
ISSUE_BODY="Body with backticks \`code\` and \$VAR." \
ISSUE_COMMENTS_FORMATTED="--- @alice em 2026-04-01T00:00:00Z ---
First comment." \
BRANCH_NAME="auto/issue-999" \
envsubst '$ISSUE_NUMBER $ISSUE_TITLE $ISSUE_BODY $ISSUE_COMMENTS_FORMATTED $BRANCH_NAME' \
  < /srv/auto-skedway/scripts/issue-resolver-prompt.md | head -30
```

Expected: variables substituted correctly. `$dollar` and `$VAR` inside the value of `$ISSUE_BODY` should appear literally (envsubst does not recursively expand variable values).

- [ ] **Step 3: Commit**

```bash
cd /srv/auto-skedway
git add scripts/issue-resolver-prompt.md
git commit -m "feat: prompt template for issue-resolver Claude session"
```

---

## Task 4: Issue selection and per-issue context fetching

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Add issue-fetching functions**

Insert before `main()`:

```bash
fetch_open_issues() {
  "$GH_BIN" issue list --repo "$REPO" --state open --limit "$MAX_ISSUES" \
    --json number,title --search "sort:created-asc"
}

fetch_issue_full() {
  local n="$1"
  "$GH_BIN" issue view "$n" --repo "$REPO" --json title,body,comments
}

format_comments() {
  jq -r '
    if (.comments | length) == 0
    then "(no comments)"
    else (.comments | map("--- @\(.author.login) em \(.createdAt) ---\n\(.body)\n") | join("\n"))
    end
  '
}
```

- [ ] **Step 2: Update main to fetch and log issues**

Replace `main()` body:

```bash
main() {
  cd "$WORKDIR"
  rotate_logs
  log "=== Run started (DRY_RUN=$DRY_RUN) ==="
  preflight

  local issues_json count
  issues_json="$(fetch_open_issues)"
  count="$(echo "$issues_json" | jq 'length')"
  log "Fetched $count open issue(s) to process"

  if [[ "$count" -eq 0 ]]; then
    log "=== No issues to process; run finished ==="
    return 0
  fi

  echo "$issues_json" | jq -c '.[]' | while read -r issue_data; do
    local n title
    n="$(echo "$issue_data" | jq -r '.number')"
    title="$(echo "$issue_data" | jq -r '.title')"
    log "--- Issue #$n: \"$title\" ---"
  done

  log "=== Run finished (selection only) ==="
}
```

- [ ] **Step 3: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean (note: shellcheck may warn about subshell `while`; this is intentional for v1 since we're only logging in this task — full loop is restructured in Task 10).

- [ ] **Step 4: Run and verify**

```bash
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh
tail -10 /srv/auto-skedway/logs/cron-issues-$(date +%Y-%m-%d).log
```

Expected: log lines listing the open issues currently in the repo, OR "No issues to process" if there are none.

- [ ] **Step 5: Verify per-issue context fetching by hand**

Pick any open issue number (or use a closed one for testing). Run:

```bash
# Use a real issue number from the repo; if none, this is a smoke test only:
N=1
gh issue view "$N" --repo cassioerodrigues/auto-skedway --json title,body,comments \
  | jq -r '
    if (.comments | length) == 0
    then "(no comments)"
    else (.comments | map("--- @\(.author.login) em \(.createdAt) ---\n\(.body)\n") | join("\n"))
    end
  '
```

Expected: either `(no comments)` or properly formatted comment blocks.

- [ ] **Step 6: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: fetch open issues and per-issue context"
```

---

## Task 5: Branch management helpers

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Add branch helpers**

Insert before `main()`:

```bash
branch_exists() {
  local b="$1"
  if git rev-parse --verify "$b" >/dev/null 2>&1; then
    return 0
  fi
  if git ls-remote --heads origin "$b" 2>/dev/null | grep -q "refs/heads/$b\$"; then
    return 0
  fi
  return 1
}

create_branch() {
  local b="$1"
  git checkout -b "$b" main >/dev/null 2>&1
}

cleanup_branch() {
  local b="$1"
  git checkout main >/dev/null 2>&1 || true
  git branch -D "$b" >/dev/null 2>&1 || true
}
```

- [ ] **Step 2: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean.

- [ ] **Step 3: Smoke test the helpers manually**

```bash
cd /srv/auto-skedway
git checkout main

# Source the script in a subshell to call helpers
bash -c '
  source /srv/auto-skedway/scripts/auto-resolve-issues.sh
  echo "branch_exists main: $(branch_exists main && echo yes || echo no)"
  echo "branch_exists nope-xyz: $(branch_exists nope-xyz && echo yes || echo no)"
' 2>&1 | tail -5
```

Wait — the script has `main "$@"` at the bottom, so sourcing it would run `main()`. Add a guard so the script can be sourced for testing.

- [ ] **Step 4: Add sourcing guard**

Replace the final line `main "$@"` with:

```bash
# Run main only when executed (not sourced)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
```

- [ ] **Step 5: Re-run smoke test**

```bash
cd /srv/auto-skedway
git checkout main
bash -c '
  source /srv/auto-skedway/scripts/auto-resolve-issues.sh
  echo "branch_exists main: $(branch_exists main && echo yes || echo no)"
  echo "branch_exists nope-xyz: $(branch_exists nope-xyz && echo yes || echo no)"
'
```

Expected:
```
branch_exists main: yes
branch_exists nope-xyz: no
```

- [ ] **Step 6: Lint and commit**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: branch existence/create/cleanup helpers"
```

---

## Task 6: fail_issue helper (failure path)

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Add fail_issue function**

Insert before `main()`:

```bash
# Comment on the issue with the failure reason and clean up the local branch.
# Usage: fail_issue <issue_number> <branch_name> <reason_string>
fail_issue() {
  local n="$1" b="$2" reason="$3"
  log "FAIL #$n: $reason"
  if [[ "$DRY_RUN" != "1" ]]; then
    "$GH_BIN" issue comment "$n" --repo "$REPO" \
      --body "Auto-resolver could not complete this issue: $reason" \
      >/dev/null 2>&1 || log "WARN: gh issue comment failed for #$n"
  fi
  cleanup_branch "$b"
}
```

- [ ] **Step 2: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: fail_issue helper to comment and cleanup on failure"
```

---

## Task 7: Claude invocation with timeout and stdout/stderr capture

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Add invoke_claude function**

Insert before `main()`:

```bash
# Render the prompt template and invoke claude -p, capturing stdout/stderr.
# Sets globals: CLAUDE_EXIT, CLAUDE_STDOUT (path to file), CLAUDE_STDERR (path to file)
# Required env: ISSUE_NUMBER, ISSUE_TITLE, ISSUE_BODY, ISSUE_COMMENTS_FORMATTED, BRANCH_NAME
invoke_claude() {
  local n="$1"
  CLAUDE_STDOUT="$(mktemp)"
  CLAUDE_STDERR="$WORKDIR/logs/cron-issue-$n-$DATE.stderr"

  log "Invoking claude (model=$MODEL_PLAN, timeout=$CLAUDE_TIMEOUT)"
  set +e
  envsubst '$ISSUE_NUMBER $ISSUE_TITLE $ISSUE_BODY $ISSUE_COMMENTS_FORMATTED $BRANCH_NAME' \
    < "$PROMPT_TEMPLATE" \
    | timeout "$CLAUDE_TIMEOUT" "$CLAUDE_BIN" -p \
        --model "$MODEL_PLAN" \
        --add-dir "$WORKDIR" \
        --dangerously-skip-permissions \
        > "$CLAUDE_STDOUT" 2> "$CLAUDE_STDERR"
  CLAUDE_EXIT=$?
  set -e
}
```

- [ ] **Step 2: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean. (Globals are intentional — used by the result-parsing function in Task 8.)

- [ ] **Step 3: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: invoke_claude with timeout and stdout/stderr capture"
```

---

## Task 8: JSON sentinel parsing and commit verification

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Add parse_claude_result function**

Insert before `main()`:

```bash
# Parse the last-line JSON sentinel from CLAUDE_STDOUT and verify a commit was made.
# Returns 0 on success (success path can proceed); non-zero on any failure.
# On failure, sets PARSE_REASON.
# On success, sets PARSE_SUMMARY.
parse_claude_result() {
  PARSE_REASON=""
  PARSE_SUMMARY=""

  if [[ "$CLAUDE_EXIT" -eq 124 ]]; then
    PARSE_REASON="Timed out after $CLAUDE_TIMEOUT (see $CLAUDE_STDERR)"
    return 1
  fi
  if [[ "$CLAUDE_EXIT" -ne 0 ]]; then
    PARSE_REASON="Claude exited with code $CLAUDE_EXIT (see $CLAUDE_STDERR)"
    return 1
  fi

  local last_line status
  last_line="$(tail -n 1 "$CLAUDE_STDOUT")"
  status="$(echo "$last_line" | jq -r '.status // "missing"' 2>/dev/null || echo "missing")"

  if [[ "$status" == "missing" ]]; then
    PARSE_REASON="Could not parse JSON sentinel from final line of stdout"
    return 1
  fi
  if [[ "$status" != "ok" ]]; then
    PARSE_REASON="$(echo "$last_line" | jq -r '.reason // "no reason given"' 2>/dev/null || echo "unknown")"
    return 1
  fi

  # Verify a commit was made on the current branch
  if [[ "$(git rev-parse HEAD)" == "$(git rev-parse main)" ]]; then
    PARSE_REASON="Claude reported ok but no commit was made"
    return 1
  fi

  PARSE_SUMMARY="$(echo "$last_line" | jq -r '.summary // "no summary"')"
  return 0
}
```

- [ ] **Step 2: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean.

- [ ] **Step 3: Smoke test the parser with mock stdout files**

```bash
cd /srv/auto-skedway
bash -c '
  source /srv/auto-skedway/scripts/auto-resolve-issues.sh

  # Case 1: ok status, but no commit (HEAD == main)
  CLAUDE_EXIT=0
  CLAUDE_STDOUT=$(mktemp)
  CLAUDE_STDERR=/tmp/dummy.stderr
  echo "Some claude blather..." > "$CLAUDE_STDOUT"
  echo "{\"status\":\"ok\",\"summary\":\"fixed bug\"}" >> "$CLAUDE_STDOUT"
  if parse_claude_result; then
    echo "case 1: unexpected ok"
  else
    echo "case 1: failed as expected: $PARSE_REASON"
  fi

  # Case 2: error status
  CLAUDE_EXIT=0
  echo "blather" > "$CLAUDE_STDOUT"
  echo "{\"status\":\"error\",\"reason\":\"too ambiguous\"}" >> "$CLAUDE_STDOUT"
  if parse_claude_result; then
    echo "case 2: unexpected ok"
  else
    echo "case 2: failed as expected: $PARSE_REASON"
  fi

  # Case 3: timeout
  CLAUDE_EXIT=124
  if parse_claude_result; then
    echo "case 3: unexpected ok"
  else
    echo "case 3: failed as expected: $PARSE_REASON"
  fi

  # Case 4: missing sentinel
  CLAUDE_EXIT=0
  echo "no json here" > "$CLAUDE_STDOUT"
  if parse_claude_result; then
    echo "case 4: unexpected ok"
  else
    echo "case 4: failed as expected: $PARSE_REASON"
  fi

  rm -f "$CLAUDE_STDOUT"
'
```

Expected:
```
case 1: failed as expected: Claude reported ok but no commit was made
case 2: failed as expected: too ambiguous
case 3: failed as expected: Timed out after 30m (see /tmp/dummy.stderr)
case 4: failed as expected: Could not parse JSON sentinel from final line of stdout
```

- [ ] **Step 4: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: parse_claude_result with JSON sentinel + commit verification"
```

---

## Task 9: Success path — push, open PR, comment on issue

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Add success-path function**

Insert before `main()`:

```bash
# On success: push branch, open PR, comment on issue.
# Args: issue_number, issue_title, branch_name, summary
# Returns 0 on success, non-zero on push or PR-create failure.
# On failure, sets PARSE_REASON for the caller to use with fail_issue.
success_open_pr() {
  local n="$1" title="$2" b="$3" summary="$4"

  if ! git push -u origin "$b" >>"$CLAUDE_STDERR" 2>&1; then
    PARSE_REASON="git push failed (see $CLAUDE_STDERR)"
    return 1
  fi

  local pr_body
  pr_body="Auto-resolver opened this PR for issue #$n.

$summary

Closes #$n"

  local pr_url
  if ! pr_url="$("$GH_BIN" pr create --repo "$REPO" --base main --head "$b" \
        --title "fix: $title (#$n)" \
        --body "$pr_body" 2>>"$CLAUDE_STDERR")"; then
    PARSE_REASON="gh pr create failed; remote branch left in place (see $CLAUDE_STDERR)"
    return 1
  fi

  "$GH_BIN" issue comment "$n" --repo "$REPO" \
    --body "Auto-resolver opened $pr_url" >/dev/null 2>&1 || \
    log "WARN: gh issue comment failed for #$n (PR was created at $pr_url)"

  log "Pushed $b, opened $pr_url, commented on issue #$n"
  return 0
}
```

- [ ] **Step 2: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: success path — push branch, open PR, comment on issue"
```

---

## Task 10: Wire main loop together

**Files:**
- Modify: `scripts/auto-resolve-issues.sh`

- [ ] **Step 1: Replace main() with full loop**

Replace the entire `main()` function with:

```bash
main() {
  cd "$WORKDIR"
  rotate_logs
  log "=== Run started (DRY_RUN=$DRY_RUN) ==="
  preflight

  local issues_json count
  issues_json="$(fetch_open_issues)"
  count="$(echo "$issues_json" | jq 'length')"
  log "Fetched $count open issue(s) to process"

  if [[ "$count" -eq 0 ]]; then
    log "=== No issues to process; run finished ==="
    return 0
  fi

  local pr_count=0 fail_count=0 skip_count=0

  # Read into array first so we don't run the loop body in a subshell
  local issue_lines=()
  while IFS= read -r line; do
    issue_lines+=("$line")
  done < <(echo "$issues_json" | jq -c '.[]')

  for issue_data in "${issue_lines[@]}"; do
    local n title b
    n="$(echo "$issue_data" | jq -r '.number')"
    title="$(echo "$issue_data" | jq -r '.title')"
    b="auto/issue-$n"

    log "--- Issue #$n: \"$title\" ---"

    if branch_exists "$b"; then
      log "Branch $b already exists (local or remote), skipping #$n"
      skip_count=$((skip_count + 1))
      continue
    fi

    # Fetch full issue context
    local issue_full body comments
    issue_full="$(fetch_issue_full "$n")"
    body="$(echo "$issue_full" | jq -r '.body // ""')"
    comments="$(echo "$issue_full" | format_comments)"

    if ! create_branch "$b"; then
      fail_issue "$n" "$b" "git checkout -b $b failed"
      fail_count=$((fail_count + 1))
      continue
    fi
    log "Branch created: $b"

    if [[ "$DRY_RUN" == "1" ]]; then
      log "DRY_RUN=1: skipping claude invocation, push, PR, and issue comment for #$n"
      cleanup_branch "$b"
      continue
    fi

    # Export prompt-template variables
    export ISSUE_NUMBER="$n"
    export ISSUE_TITLE="$title"
    export ISSUE_BODY="$body"
    export ISSUE_COMMENTS_FORMATTED="$comments"
    export BRANCH_NAME="$b"

    invoke_claude "$n"

    if ! parse_claude_result; then
      fail_issue "$n" "$b" "$PARSE_REASON"
      fail_count=$((fail_count + 1))
      rm -f "$CLAUDE_STDOUT"
      continue
    fi

    log "Claude exit=0, status=ok, summary=\"$PARSE_SUMMARY\""

    if ! success_open_pr "$n" "$title" "$b" "$PARSE_SUMMARY"; then
      fail_issue "$n" "$b" "$PARSE_REASON"
      fail_count=$((fail_count + 1))
      rm -f "$CLAUDE_STDOUT"
      continue
    fi

    pr_count=$((pr_count + 1))
    git checkout main >/dev/null 2>&1
    rm -f "$CLAUDE_STDOUT"
  done

  log "=== Run finished: $pr_count PR(s) opened, $fail_count failure(s), $skip_count skipped ==="
}
```

- [ ] **Step 2: Lint**

```bash
shellcheck /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: clean.

- [ ] **Step 3: Run dry-run end to end**

```bash
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh
tail -30 /srv/auto-skedway/logs/cron-issues-$(date +%Y-%m-%d).log
```

Expected sequence (assuming there are open issues):
```
=== Run started (DRY_RUN=1) ===
Pre-flight ok ...
Fetched N open issue(s) to process
--- Issue #X: "..." ---
Branch created: auto/issue-X
DRY_RUN=1: skipping claude invocation, push, PR, and issue comment for #X
... (repeated per issue) ...
=== Run finished: 0 PR(s) opened, 0 failure(s), 0 skipped ===
```

(The branch should not exist after dry-run; cleanup_branch was called.)

- [ ] **Step 4: Verify no branches were leaked**

```bash
cd /srv/auto-skedway
git branch | grep '^.*auto/' || echo "no auto branches — good"
git ls-remote --heads origin 'auto/*' 2>/dev/null || echo "no remote auto branches — good"
```

Expected: no `auto/*` branches locally or remotely.

- [ ] **Step 5: Commit**

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "feat: wire full main loop with success/fail/skip accounting"
```

---

## Task 11: Live single-issue smoke test

**Files:**
- None modified (manual verification step)
- Test artifact: a real GitHub issue created for the test

- [ ] **Step 1: Create a tiny test issue manually**

Open a deliberately small, unambiguous issue in `cassioerodrigues/auto-skedway`. Example:

```bash
gh issue create --repo cassioerodrigues/auto-skedway \
  --title "test: add empty-line at end of README" \
  --body "Please ensure README.md ends with exactly one trailing newline. This issue exists to smoke-test the auto-resolver."
```

Note the issue number returned (call it `TEST_N`).

- [ ] **Step 2: Confirm only that issue is the oldest open**

```bash
gh issue list --repo cassioerodrigues/auto-skedway --state open --limit 3 \
  --json number,title --search "sort:created-asc" | jq
```

If older open issues exist, either close them first or temporarily set `MAX_ISSUES=1` and ensure the test issue is the oldest. **Do not run live against a real bug for the first smoke test.**

- [ ] **Step 3: Run the script live (no DRY_RUN)**

```bash
/srv/auto-skedway/scripts/auto-resolve-issues.sh
```

This will take up to 30 minutes. Watch the log file in another terminal:

```bash
tail -f /srv/auto-skedway/logs/cron-issues-$(date +%Y-%m-%d).log
```

Expected on success:
```
--- Issue #TEST_N: "test: add empty-line at end of README" ---
Branch created: auto/issue-TEST_N
Invoking claude (model=claude-opus-4-7, timeout=30m)
Claude exit=0, status=ok, summary="..."
Pushed auto/issue-TEST_N, opened https://github.com/.../pull/X, commented on issue #TEST_N
=== Run finished: 1 PR(s) opened, 0 failure(s), 0 skipped ===
```

- [ ] **Step 4: Verify on GitHub**

- A new branch `auto/issue-TEST_N` exists on the remote.
- A PR is open against `main` with a `Closes #TEST_N` trailer in its body.
- The issue has a comment from `@cassioerodrigues` (or whoever the gh token belongs to) saying "Auto-resolver opened …".

- [ ] **Step 5: Clean up the smoke test**

After verifying, close the PR without merging (or merge it if the change is harmless), delete the test branch, and close the issue.

```bash
gh pr close <PR_NUMBER> --repo cassioerodrigues/auto-skedway --delete-branch
gh issue close TEST_N --repo cassioerodrigues/auto-skedway
```

- [ ] **Step 6: No commit** (no code changed in this task)

---

## Task 12: Crontab installation

**Files:**
- Modify: root crontab (via `crontab -e`)

- [ ] **Step 1: Install crontab entry**

```bash
( crontab -l 2>/dev/null ; echo "0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1" ) | crontab -
```

- [ ] **Step 2: Verify**

```bash
crontab -l
```

Expected:
```
0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1
```

- [ ] **Step 3: Verify timezone of cron daemon**

```bash
systemctl show cron 2>/dev/null | grep -i timezone
date
```

The cron daemon inherits the system timezone (`America/Sao_Paulo`), so `0 2 * * *` will fire at 02:00 BRT.

- [ ] **Step 4: No commit** (crontab is host-local, not repo state)

- [ ] **Step 5: Document the crontab entry in the repo**

Add a note to the spec or create a brief operational README:

```bash
cat >> /srv/auto-skedway/scripts/README.md <<'EOF'
# scripts/

Automation scripts for this repo.

## auto-resolve-issues.sh

Nightly cron job. Picks up to 3 oldest open GitHub issues, plans with Claude
Opus, dispatches Haiku subagents per task, and opens 1 PR per resolved issue.
Failures comment on the issue.

**Crontab entry (root):**

```
0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1
```

**Manual run (for debugging):**

```bash
DRY_RUN=1 /srv/auto-skedway/scripts/auto-resolve-issues.sh   # safe — no claude, no PRs
/srv/auto-skedway/scripts/auto-resolve-issues.sh             # live
```

**Logs:**

- `logs/cron-issues-YYYY-MM-DD.log` — per-run log, retained 30 days.
- `logs/cron-issue-NNN-YYYY-MM-DD.stderr` — per-issue Claude stderr, retained 30 days.
- `logs/cron-stdout.log` — cron's own stdout/stderr, append-only.

**Spec:** `docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md`
EOF
```

- [ ] **Step 6: Commit the README**

```bash
cd /srv/auto-skedway
git add scripts/README.md
git commit -m "docs: operational README for scripts/auto-resolve-issues.sh"
```

---

## Done criteria

- All 12 tasks above checked off.
- `shellcheck` clean on `scripts/auto-resolve-issues.sh`.
- Live single-issue smoke test produced an actual PR on GitHub.
- Crontab entry visible in `crontab -l`.
- Repo contains: `scripts/auto-resolve-issues.sh`, `scripts/issue-resolver-prompt.md`, `scripts/README.md`.
