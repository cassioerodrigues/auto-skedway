# Cron Issue Resolver — Superpowers Workflow Amendment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch the per-issue Claude session's workflow from the native `Plan` agent + Haiku subagents to the superpowers workflow (conditional brainstorming, writing-plans, conditional TDD, Sonnet 4.6 implementation subagents, Opus reviewer with up to 2 iterations), then install the crontab entry to enable the nightly run.

**Architecture:** Three documentation/text edits (prompt template rewrite + spec amendment cross-link + original-plan annotation) followed by host-level crontab installation. The bash orchestrator (`scripts/auto-resolve-issues.sh`) is **not modified**. No code logic changes — only the markdown content of the rendered prompt and crontab entry on the host.

**Tech Stack:** Markdown, `envsubst` (GNU gettext) for variable rendering, `crontab` for installation, `git`. No new dependencies.

---

## Spec reference

`docs/superpowers/specs/2026-04-30-cron-issue-resolver-superpowers-amendment.md` (commit `d8d21f3` on branch `feat/cron-issue-resolver`).

## File layout impacted

```
/srv/auto-skedway/
├── scripts/
│   └── issue-resolver-prompt.md         # MODIFIED in Task 1 (workflow rewrite)
├── docs/superpowers/specs/
│   └── 2026-04-30-cron-issue-resolver-design.md   # MODIFIED in Task 2 (cross-link)
├── docs/superpowers/plans/
│   └── 2026-04-30-cron-issue-resolver.md          # MODIFIED in Task 3 (annotate Task 3)
└── (root crontab on host — installed in Task 5)
```

No new files. No bash changes. No Python changes.

---

## Task 1: Rewrite the prompt template's workflow section

**Files:**
- Modify: `scripts/issue-resolver-prompt.md` — replace section "How to work" (lines 21-42) and append a cleanup-on-error item to "Hard constraints" (line 56-62).

The `envsubst` variables (`${ISSUE_NUMBER}`, `${ISSUE_TITLE}`, `${ISSUE_BODY}`, `${ISSUE_COMMENTS_FORMATTED}`, `${BRANCH_NAME}`) MUST remain in the file unchanged in spelling and position within the "Context" section.

- [ ] **Step 1: Read the current file to confirm starting state**

```bash
cat /srv/auto-skedway/scripts/issue-resolver-prompt.md
```

Expected: file matches the version committed in `fff1654`. Sections present: job statement, Context, How to work (steps 1-7), Output contract, Hard constraints.

- [ ] **Step 2: Replace section "How to work" entirely**

Use the Edit tool to replace lines 21-42 (the current "# How to work" section ending right before "# Output contract — REQUIRED") with this exact content:

```markdown
# How to work

You have access to the superpowers skill plugin via the Skill tool. The workflow below is required, not optional.

## 1. Understand the request

Read the issue title, body, and all comments above. If a later comment from the issue author or a maintainer contradicts the original body, prefer the comment. Then explore relevant code with Read, Grep, and Bash to confirm your understanding.

## 2. Decide whether to brainstorm

Classify the issue based on what you read:

- **Bug with clear repro / small targeted change** — skip brainstorming, go to step 3.
- **Feature, ambiguous scope, multiple plausible designs, or open-ended change** — invoke `superpowers:brainstorming`. You are headless with no human to dialog with, so answer your own clarifying questions from the issue context and code exploration, then write the spec yourself. Save it to `docs/superpowers/specs/<today>-issue-${ISSUE_NUMBER}-<topic-slug>.md` using today's actual date (run `date +%Y-%m-%d`).

## 3. Plan

Invoke `superpowers:writing-plans`. Save the resulting plan to `docs/superpowers/plans/<today>-issue-${ISSUE_NUMBER}-<topic-slug>.md`.

## 4. Implement step by step

For each step in the plan, decide whether TDD applies:

- **Bug fix with reproducible failure, new function, or behavior change** — TDD required. Write a failing test first, then the minimal implementation that makes it pass.
- **Pure documentation, configuration, or visual UI change without logic** — skip tests. Note "no test (docs/config/visual)" in the eventual commit body.

Dispatch independent plan steps in parallel using the `superpowers:subagent-driven-development` pattern. Subagent invocations:

```
Agent(subagent_type="general-purpose", model="sonnet",
      prompt="<the specific step including file paths, acceptance criteria, and whether TDD applies>")
```

Sequential / dependent steps run one at a time. After all subagents return, read the changed files yourself to verify the plan was followed and the implementation matches the issue.

## 5. Code review

Invoke `superpowers:requesting-code-review`. Dispatch the reviewer subagent:

```
Agent(subagent_type="superpowers:code-reviewer", model="opus",
      prompt="<diff summary + plan + acceptance criteria from the issue>")
```

Track iteration count yourself:

- **Approved** — proceed to step 6.
- **Reproved, iteration 1** — dispatch a Sonnet subagent to apply the requested fixes, then re-run the reviewer.
- **Reproved, iteration 2** — terminate with the failure sentinel: `{"status":"error","reason":"code review failed after 2 iterations: <one-line summary of feedback>"}`. Run cleanup (see Hard constraints) before printing.

## 6. Commit on the current branch

A single commit including code, plan markdown, and spec markdown (if you wrote one):

```
git add -A
git commit -m "fix: <one-line summary> (closes #${ISSUE_NUMBER})"
```

In the commit body, briefly note any plan steps that skipped TDD and why.

Do NOT push. Do NOT open the PR. Do NOT comment on the issue. The orchestrator script handles those.

## 7. Print the JSON sentinel

The very last line of your stdout MUST be a single-line JSON object — no markdown, no surrounding text. See "Output contract" below for the exact format.
```

- [ ] **Step 3: Append a cleanup-on-error item to "Hard constraints"**

Use the Edit tool to add this bullet at the end of the "# Hard constraints" section (after the existing four bullets):

```markdown
- **Cleanup on error:** before printing the failure sentinel, leave the working tree clean. If you created `docs/superpowers/specs/` or `docs/superpowers/plans/` artifacts during a failed run, remove them: `git clean -fd docs/superpowers/specs docs/superpowers/plans && git checkout -- .`. Do NOT commit on failure.
```

- [ ] **Step 4: Verify envsubst variables are still intact**

Run:

```bash
grep -E '\$\{(ISSUE_NUMBER|ISSUE_TITLE|ISSUE_BODY|ISSUE_COMMENTS_FORMATTED|BRANCH_NAME)\}' /srv/auto-skedway/scripts/issue-resolver-prompt.md
```

Expected output: at least 5 lines, one per variable. If any variable is missing from the file, restore it (it must appear in the "# Context" section as it did before).

- [ ] **Step 5: Verify the rendered template is well-formed**

Render with sample values and inspect the output:

```bash
cd /srv/auto-skedway && \
  ISSUE_NUMBER=999 \
  ISSUE_TITLE="Sample title" \
  ISSUE_BODY="Sample body" \
  ISSUE_COMMENTS_FORMATTED="--- @user em 2026-04-30T10:00:00Z ---\nSample comment" \
  BRANCH_NAME="auto/issue-999" \
  envsubst '${ISSUE_NUMBER} ${ISSUE_TITLE} ${ISSUE_BODY} ${ISSUE_COMMENTS_FORMATTED} ${BRANCH_NAME}' \
  < scripts/issue-resolver-prompt.md > /tmp/rendered-prompt.md
wc -l /tmp/rendered-prompt.md
grep -c 'superpowers:' /tmp/rendered-prompt.md
grep -c '999' /tmp/rendered-prompt.md
```

Expected:
- `wc -l`: at least 90 lines.
- `grep -c 'superpowers:'`: at least 4 (brainstorming, writing-plans, subagent-driven-development, requesting-code-review, code-reviewer).
- `grep -c '999'`: at least 2 (occurrences of the substituted issue number).

If any expected count is wrong, re-read the template and fix the missing reference.

- [ ] **Step 6: Commit**

```bash
cd /srv/auto-skedway
git add scripts/issue-resolver-prompt.md
git commit -m "feat: rewrite resolver prompt to use superpowers workflow

Replace native Plan agent + Haiku subagents with superpowers
workflow: conditional brainstorming, writing-plans, conditional
TDD, Sonnet 4.6 implementation subagents, Opus code-reviewer
with up to 2 iterations. Add cleanup-on-error constraint.

See docs/superpowers/specs/2026-04-30-cron-issue-resolver-superpowers-amendment.md"
```

---

## Task 2: Cross-link the original spec to the amendment

**Files:**
- Modify: `docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md` — section "Prompt template (`scripts/issue-resolver-prompt.md`)" (lines 69-85).

- [ ] **Step 1: Read the current section**

```bash
sed -n '69,85p' /srv/auto-skedway/docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md
```

Confirm the section starts with "### Prompt template" and lists the 6 numbered template instructions (read issue, call Plan agent, dispatch Haiku, validate, commit, print sentinel).

- [ ] **Step 2: Replace the section with an amendment notice**

Use Edit to replace the entire block from "### Prompt template (`scripts/issue-resolver-prompt.md`)" through the line before "### Claude invocation" with:

```markdown
### Prompt template (`scripts/issue-resolver-prompt.md`)

Uses `envsubst` substitution for: `$ISSUE_NUMBER`, `$ISSUE_TITLE`, `$ISSUE_BODY`, `$ISSUE_COMMENTS_FORMATTED`, `$BRANCH_NAME`.

> **Amended 2026-04-30:** the per-issue workflow originally described here (native `Plan` agent + Haiku subagents) was replaced by the superpowers workflow (conditional brainstorming, writing-plans, conditional TDD, Sonnet 4.6 implementation subagents, Opus code-reviewer with up to 2 iterations). See `docs/superpowers/specs/2026-04-30-cron-issue-resolver-superpowers-amendment.md` for the current contract.

The `closes #N` trailer in the eventual commit makes GitHub auto-close the issue when the PR is merged.
```

- [ ] **Step 3: Confirm the rest of the spec still flows**

```bash
grep -n -E '^###' /srv/auto-skedway/docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md
```

Expected sections in order: Issue selection, Per-issue context for Claude, Prompt template, Claude invocation, Bash decision logic per issue, Pre-flight protections, Out of scope (deferred), Per-run log, Per-issue stderr, Log rotation. Section "Prompt template" must still be present and now contains the amendment notice.

- [ ] **Step 4: Commit**

```bash
cd /srv/auto-skedway
git add docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md
git commit -m "docs: cross-link original spec to superpowers amendment

The 'Prompt template' section now points readers at the
amendment doc which defines the current per-issue workflow."
```

---

## Task 3: Annotate the original implementation plan's Task 3

**Files:**
- Modify: `docs/superpowers/plans/2026-04-30-cron-issue-resolver.md` — Task 3 section ("Prompt template file").

- [ ] **Step 1: Locate Task 3 in the plan**

```bash
grep -n '^## Task 3:' /srv/auto-skedway/docs/superpowers/plans/2026-04-30-cron-issue-resolver.md
```

Confirm the line "## Task 3: Prompt template file" exists and note its line number.

- [ ] **Step 2: Insert an amendment note immediately under the Task 3 heading**

Use Edit to insert this paragraph between the "## Task 3: Prompt template file" heading and the next content (whether that next content is a `**Files:**` block, a step, or another heading):

```markdown
> **Amended 2026-04-30:** the prompt template content originally created by this task was replaced by the superpowers workflow described in `docs/superpowers/specs/2026-04-30-cron-issue-resolver-superpowers-amendment.md` and implemented by `docs/superpowers/plans/2026-04-30-cron-issue-resolver-superpowers-amendment.md`. The steps below remain as the historical Task 3; the file content currently on `feat/cron-issue-resolver` reflects the amendment, not these steps.
```

- [ ] **Step 3: Commit**

```bash
cd /srv/auto-skedway
git add docs/superpowers/plans/2026-04-30-cron-issue-resolver.md
git commit -m "docs: annotate original plan Task 3 with amendment pointer"
```

---

## Task 4: Render and visually inspect the final template

**Files:** none modified — verification only.

- [ ] **Step 1: Render with sample values**

```bash
cd /srv/auto-skedway && \
  ISSUE_NUMBER=42 \
  ISSUE_TITLE="Login redirect loop after password change" \
  ISSUE_BODY="When a user changes their password, they get redirected to /login indefinitely." \
  ISSUE_COMMENTS_FORMATTED="--- @cassio em 2026-04-29T12:00:00Z ---
Confirmed reproducible on staging." \
  BRANCH_NAME="auto/issue-42" \
  envsubst '${ISSUE_NUMBER} ${ISSUE_TITLE} ${ISSUE_BODY} ${ISSUE_COMMENTS_FORMATTED} ${BRANCH_NAME}' \
  < scripts/issue-resolver-prompt.md > /tmp/rendered-prompt.md
```

- [ ] **Step 2: Inspect the rendered output**

```bash
less /tmp/rendered-prompt.md
```

Visually confirm:
- Issue 42 title, body, and comment appear in the "Context" section.
- The "How to work" section shows the 7 superpowers steps in order, not the old 6 steps with `Plan` and Haiku.
- Subagent invocation snippets reference `model="sonnet"` and `model="opus"`.
- The "Hard constraints" section ends with the cleanup-on-error bullet.
- The "Output contract" section is unchanged.

- [ ] **Step 3: Confirm no leftover envsubst variables**

```bash
grep -n '\${' /tmp/rendered-prompt.md
```

Expected: no output. (All `${...}` placeholders should have been substituted.) If any remain, identify the variable and either add it to the `envsubst` allowlist in the bash orchestrator or escape it in the template.

- [ ] **Step 4: Cleanup the rendered file**

```bash
rm /tmp/rendered-prompt.md
```

- [ ] **Step 5: No commit** (this task only verifies — no code or doc changes were produced).

---

## Task 5: Install the crontab entry

**Files:**
- Modify: root crontab on host (not in repo).
- Create: `scripts/README.md` — short note documenting the crontab line for repo-side reference.

This task adapts Task 12 from the original implementation plan. The user has chosen to skip Task 11 (the live single-issue smoke test) and proceed directly to crontab installation.

- [ ] **Step 1: Confirm the resolver script is present and executable on the branch**

```bash
ls -l /srv/auto-skedway/scripts/auto-resolve-issues.sh
```

Expected: file exists, mode includes `x` (executable). If not executable, run `chmod +x /srv/auto-skedway/scripts/auto-resolve-issues.sh`.

- [ ] **Step 2: Confirm the host's cron daemon timezone**

```bash
timedatectl | grep 'Time zone'
```

Expected: `America/Sao_Paulo`. If the host shows a different timezone, the cron expression `0 2 * * *` will fire at 02:00 in the host's timezone, not BRT — note this in the README created in Step 6 if applicable.

- [ ] **Step 3: Confirm the absolute path to the `claude` binary**

```bash
which claude
ls -l /root/.local/bin/claude 2>/dev/null || true
```

Expected: `claude` resolves to the path used as `CLAUDE_BIN` in the orchestrator script. If the path differs, update `CLAUDE_BIN` in `scripts/auto-resolve-issues.sh` (this is a small bug fix in the orchestrator and gets its own commit per Step 7).

- [ ] **Step 4: Inspect the current root crontab**

```bash
crontab -l 2>/dev/null || echo "(no crontab)"
```

Note any existing entries — the new line will be appended to the end. If a prior auto-resolver entry already exists (from an earlier install attempt), do NOT duplicate it; replace it in Step 5.

- [ ] **Step 5: Install the crontab entry**

```bash
( crontab -l 2>/dev/null | grep -v 'auto-resolve-issues.sh' ; \
  echo '0 2 * * * /srv/auto-skedway/scripts/auto-resolve-issues.sh >> /srv/auto-skedway/logs/cron-stdout.log 2>&1' \
) | crontab -
crontab -l | grep auto-resolve-issues.sh
```

Expected: the final command prints exactly one line containing the resolver path. If two lines appear, deduplicate manually with `crontab -e` and remove duplicates.

- [ ] **Step 6: Document the crontab entry in the repo**

Create `/srv/auto-skedway/scripts/README.md` with this content:

```markdown
# Auto-resolver scripts

## Files

- `auto-resolve-issues.sh` — bash orchestrator. Selects up to 3 oldest open issues, branches off `main`, invokes `claude -p` per issue, opens a PR or comments on failure.
- `issue-resolver-prompt.md` — prompt template rendered via `envsubst` and piped to the Claude session.

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
```

- [ ] **Step 7: Commit the README (and `CLAUDE_BIN` fix if Step 3 found one)**

If Step 3 required updating `CLAUDE_BIN`, stage and commit that change first as a separate commit:

```bash
cd /srv/auto-skedway
git add scripts/auto-resolve-issues.sh
git commit -m "fix: correct CLAUDE_BIN path to match host install"
```

Then commit the README:

```bash
cd /srv/auto-skedway
git add scripts/README.md
git commit -m "docs: README for scripts/ documenting crontab entry"
```

---

## Self-review checklist (run after the plan is fully executed)

- All five tasks above produced commits on `feat/cron-issue-resolver` (Task 4 produces no commit by design).
- `scripts/issue-resolver-prompt.md` rendered with sample values shows the new superpowers workflow and no unsubstituted `${...}` placeholders.
- `crontab -l` shows exactly one line referencing `auto-resolve-issues.sh`.
- Branch `feat/cron-issue-resolver` is ready for the user to open a PR (the user owns the PR and merge — no automated push to `origin` from this plan).
