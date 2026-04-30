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

# --- Main entry point (filled in later tasks) ---
main() {
  cd "$WORKDIR"
  rotate_logs
  log "=== Run started (DRY_RUN=$DRY_RUN) ==="
  log "=== Run finished (skeleton only) ==="
}

main "$@"
