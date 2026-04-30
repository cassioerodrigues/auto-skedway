#!/usr/bin/env bash
# shellcheck disable=SC2034  # TEMPORARY: config vars consumed in Tasks 4-10; remove after Task 10
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

  echo "$issues_json" | jq -c '.[]' | while read -r issue_data; do
    local n title
    n="$(echo "$issue_data" | jq -r '.number')"
    title="$(echo "$issue_data" | jq -r '.title')"
    log "--- Issue #$n: \"$title\" ---"
  done

  log "=== Run finished (selection only) ==="
}

main "$@"
