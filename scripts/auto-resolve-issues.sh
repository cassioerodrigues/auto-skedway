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
  log "ABORT: $*" || echo "[ABORT] $*" >&2
  echo "[ABORT] $*" >&2
  exit 1
}

# --- Log rotation ---
rotate_logs() {
  find "$WORKDIR/logs" -name 'cron-issue*' -mtime "+$LOG_RETENTION_DAYS" -delete 2>/dev/null || true
}

# --- Pre-flight checks ---
preflight() {
  cd "$WORKDIR"
  git checkout main >/dev/null 2>&1 || abort "git checkout main failed"
  git pull --ff-only origin main >/dev/null 2>&1 || abort "git pull --ff-only failed (non-FF or network error)"
  if [[ -n "$(git status --porcelain)" ]]; then
    abort "dirty working tree on main — refusing to run"
  fi
  log "Pre-flight ok (on main, clean, up to date)"
}

# --- Issue fetching ---
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
  # Discard anything Claude left behind so the next preflight does not abort
  # with "dirty working tree". Untracked plan/spec dirs first, then any
  # tracked-but-uncommitted edits on the failed branch (about to be deleted).
  git clean -fd docs/superpowers/specs docs/superpowers/plans >/dev/null 2>&1 || true
  git checkout -- . >/dev/null 2>&1 || true
  cleanup_branch "$b"
}

# Render the prompt template and invoke claude -p, capturing stdout/stderr.
# Sets globals: CLAUDE_EXIT, CLAUDE_STDOUT (path to file), CLAUDE_STDERR (path to file)
# Required env: ISSUE_NUMBER, ISSUE_TITLE, ISSUE_BODY, ISSUE_COMMENTS_FORMATTED, BRANCH_NAME
invoke_claude() {
  local n="$1"
  local ts
  ts="$(date +%H%M%S)"
  # Per-attempt timestamped paths so retries within a day don't truncate
  # each other's output. Both files are kept regardless of exit status —
  # rotate_logs prunes them after LOG_RETENTION_DAYS.
  CLAUDE_STDOUT="$WORKDIR/logs/cron-issue-$n-$DATE-$ts.stdout"
  CLAUDE_STDERR="$WORKDIR/logs/cron-issue-$n-$DATE-$ts.stderr"

  log "Invoking claude (model=$MODEL_PLAN, timeout=$CLAUDE_TIMEOUT)"
  set +e
  # shellcheck disable=SC2016  # single-quoted list is intentional envsubst filter syntax
  envsubst '$ISSUE_NUMBER $ISSUE_TITLE $ISSUE_BODY $ISSUE_COMMENTS_FORMATTED $BRANCH_NAME' \
    < "$PROMPT_TEMPLATE" \
    | IS_SANDBOX=1 timeout "$CLAUDE_TIMEOUT" "$CLAUDE_BIN" -p \
        --model "$MODEL_PLAN" \
        --add-dir "$WORKDIR" \
        --dangerously-skip-permissions \
        > "$CLAUDE_STDOUT" 2> "$CLAUDE_STDERR"
  CLAUDE_EXIT=$?
  set -e
}

# Parse the last-line JSON sentinel from CLAUDE_STDOUT and verify a commit was made.
# Returns 0 on success (success path can proceed); non-zero on any failure.
# On failure, sets PARSE_REASON.
# On success, sets PARSE_SUMMARY.
parse_claude_result() {
  # shellcheck disable=SC2034
  PARSE_REASON=""
  # shellcheck disable=SC2034
  PARSE_SUMMARY=""

  if [[ "$CLAUDE_EXIT" -eq 124 ]]; then
    # shellcheck disable=SC2034
    PARSE_REASON="Timed out after $CLAUDE_TIMEOUT (see $CLAUDE_STDERR)"
    return 1
  fi
  if [[ "$CLAUDE_EXIT" -ne 0 ]]; then
    # shellcheck disable=SC2034
    PARSE_REASON="Claude exited with code $CLAUDE_EXIT (see $CLAUDE_STDERR)"
    return 1
  fi

  local last_line status
  last_line="$(tail -n 1 "$CLAUDE_STDOUT")"
  status="$(echo "$last_line" | jq -r '.status // "missing"' 2>/dev/null || echo "missing")"

  if [[ "$status" == "missing" ]]; then
    # shellcheck disable=SC2034
    PARSE_REASON="Could not parse JSON sentinel from final line of stdout"
    return 1
  fi
  if [[ "$status" != "ok" ]]; then
    # shellcheck disable=SC2034
    PARSE_REASON="$(echo "$last_line" | jq -r '.reason // "no reason given"' 2>/dev/null || echo "unknown")"
    return 1
  fi

  # Verify a commit was made on the current branch
  if [[ "$(git rev-parse HEAD)" == "$(git rev-parse main)" ]]; then
    # shellcheck disable=SC2034
    PARSE_REASON="Claude reported ok but no commit was made"
    return 1
  fi

  # shellcheck disable=SC2034
  PARSE_SUMMARY="$(echo "$last_line" | jq -r '.summary // "no summary"')"
  return 0
}

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

# --- Main entry point ---
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
      continue
    fi

    log "Claude exit=0, status=ok, summary=\"$PARSE_SUMMARY\""

    if ! success_open_pr "$n" "$title" "$b" "$PARSE_SUMMARY"; then
      fail_issue "$n" "$b" "$PARSE_REASON"
      fail_count=$((fail_count + 1))
      continue
    fi

    pr_count=$((pr_count + 1))
    git checkout main >/dev/null 2>&1
  done

  log "=== Run finished: $pr_count PR(s) opened, $fail_count failure(s), $skip_count skipped ==="
}

# Run main only when executed (not sourced)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
