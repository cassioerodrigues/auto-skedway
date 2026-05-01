# Cron Issue Resolver — Superpowers Workflow Amendment

**Date:** 2026-04-30
**Status:** Approved (pending implementation plan)
**Supersedes:** Section "Prompt template" of `2026-04-30-cron-issue-resolver-design.md`
**Repo:** `cassioerodrigues/auto-skedway`
**Branch:** `feat/cron-issue-resolver`

## Why this amendment

The original design instructs the per-issue Claude session to use the native `Agent(subagent_type="Plan")` agent and dispatch `Agent(subagent_type="general-purpose", model="haiku")` subagents for parallel work. After implementation through Task 10, the user revised this requirement: the resolver should instead use the **superpowers workflow** (brainstorming → writing-plans → TDD → subagent-driven-development → requesting-code-review), with **Sonnet 4.6** subagents for implementation and **Opus** for code review.

Tests for the resolver itself are out of scope for this work — the user owns PR validation and testing.

## Scope of change

This amendment changes **only** what the rendered prompt template (`scripts/issue-resolver-prompt.md`) instructs Claude to do once it starts processing a single issue. The bash orchestrator (`scripts/auto-resolve-issues.sh`), issue selection, branch management, sentinel parsing, push/PR/comment, error handling, logging, and crontab installation are **unchanged**.

## New per-issue workflow

The Claude Opus session, running headlessly via `claude -p --dangerously-skip-permissions`, executes the following sequence:

1. **Read context.** Issue title, body, comments (already injected via `envsubst`). Explore relevant code with Read/Grep/Bash.

2. **Decide whether to brainstorm.** Conditional on issue type:
   - Bug with clear repro / small targeted change → skip brainstorming.
   - Feature / open-ended change / ambiguous scope → invoke `superpowers:brainstorming` (solo, no human to dialog with — produces a spec from the issue and code exploration). Spec is written to `docs/superpowers/specs/YYYY-MM-DD-issue-NNN-<topic>.md`.

3. **Plan.** Invoke `superpowers:writing-plans` to produce an implementation plan, written to `docs/superpowers/plans/YYYY-MM-DD-issue-NNN-<topic>.md`.

4. **Implement step by step.** For each plan step:
   - **TDD decision (per step):** if the step has testable logic (bug fix, new function, behavior change), TDD is required — write a failing test first, then implementation that makes it pass. If the step is purely documentation, configuration, or visual UI without logic, skip tests and note the rationale in the eventual commit message.
   - **Dispatch implementation:** for independent steps, dispatch in parallel via `superpowers:subagent-driven-development` pattern. Subagent calls use:
     `Agent(subagent_type="general-purpose", model="sonnet", prompt="<step + acceptance criteria + file paths>")`.
     Sequential / dependent steps run one at a time.

5. **Code review.** Invoke `superpowers:requesting-code-review`. The review is performed by an in-session subagent:
   `Agent(subagent_type="superpowers:code-reviewer", model="opus", prompt="<diff + plan + acceptance criteria>")`.
   Outcome handling:
   - **Approved:** proceed to commit.
   - **Reprovado, iteração 1:** dispatch a Sonnet subagent to apply the requested fixes; re-run the Opus reviewer.
   - **Reprovado, iteração 2:** terminate with sentinel `{"status":"error","reason":"code review failed after 2 iterations: <summary>"}`. Do not commit.

6. **Commit.** Single commit on the current branch including code, plan markdown, and spec markdown (if brainstorming ran):
   ```
   git add -A
   git commit -m "fix: <one-line summary> (closes #${ISSUE_NUMBER})"
   ```
   Do NOT push. Do NOT open the PR. The orchestrator script handles that.

7. **Print JSON sentinel** as the final stdout line, identical contract to the original spec:
   - Success: `{"status":"ok","summary":"<one-sentence description>"}`
   - Failure: `{"status":"error","reason":"<short reason>"}`

## Failure modes (new)

The orchestrator's bash decision logic is unchanged — it still reads only the last-line sentinel. New failure modes that the prompt must handle internally and surface as `status=error`:

| Failure point | How Claude detects it | Sentinel reason |
|---|---|---|
| `superpowers:brainstorming` does not produce a spec file | Verify spec file exists after invocation | "brainstorming failed to produce spec" |
| `superpowers:writing-plans` does not produce a plan file | Verify plan file exists | "planning failed" |
| Implementation subagent returns error or empty result | Task tool error / no diff | Retry once; if still failing → "subagent failed for step: <id>" |
| Code review reprova after 2 iterations | Loop counter inside Claude's logic | "code review failed after 2 iterations: <reviewer feedback summary>" |
| 30-minute timeout | bash `timeout` returns 124 (handled by orchestrator) | (orchestrator action — comments "timed out after 30min", unchanged) |

If any internal step fails after artifacts (plan/spec markdown) have been written, Claude must `git checkout -- .` and `git clean -fd docs/superpowers/{specs,plans}/` to leave a clean working tree before printing the error sentinel. The orchestrator's branch cleanup runs after.

## PR contents change

PRs created by the resolver will now typically contain three additional file types beyond code changes:

- `docs/superpowers/plans/YYYY-MM-DD-issue-NNN-*.md` — always.
- `docs/superpowers/specs/YYYY-MM-DD-issue-NNN-*.md` — when brainstorming ran.
- Test files (in the test layout the project already uses) — when TDD applied.

Reviewer (the user) sees the resolver's reasoning trail. Plan/spec accumulate in the repo as historical record of automated work.

## Files changed by this amendment

| File | Change | Status |
|---|---|---|
| `scripts/issue-resolver-prompt.md` | Replace step-by-step "How to work" section with the new superpowers workflow described above. Keep all `envsubst` variables (`${ISSUE_NUMBER}`, `${ISSUE_TITLE}`, `${ISSUE_BODY}`, `${ISSUE_COMMENTS_FORMATTED}`, `${BRANCH_NAME}`) unchanged. | Will be modified |
| `docs/superpowers/specs/2026-04-30-cron-issue-resolver-design.md` | Update "Prompt template" section to reference this amendment and remove obsolete instructions (Plan agent, Haiku model). | Will be modified |
| `docs/superpowers/plans/2026-04-30-cron-issue-resolver.md` | Update Task 3 ("Prompt template file") to describe the new template content. | Will be modified |
| `scripts/auto-resolve-issues.sh` | None — `MODEL_PLAN="claude-opus-4-7"` and `CLAUDE_TIMEOUT="30m"` are kept. | Unchanged |

## Constraints preserved from original spec

- Single git commit per issue with `closes #N` trailer.
- `--dangerously-skip-permissions` required (no human to approve tool calls).
- 30-minute hard timeout per issue.
- JSON sentinel as final stdout line.
- Bash orchestrator never inspects intermediate output — only exit code + last line.
- No push, no PR, no issue comment from inside Claude session — bash owns those.

## Out of scope (unchanged from original)

- Auto-merge on green CI.
- Retry of failed issues from prior nights.
- `auto-skip` label or stop-list.
- Email/Slack notifications.
- Tests for the resolver itself (user-owned).

## Open assumptions to verify during implementation

- `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:subagent-driven-development`, `superpowers:test-driven-development`, and `superpowers:requesting-code-review` skills are available to a `claude -p` headless session under `--dangerously-skip-permissions`. (Skills come from the user's plugin install at `/root/.claude/plugins/`; they are loaded via the Skill tool. Should work in headless mode but worth a smoke check.)
- The `superpowers:code-reviewer` subagent type is invocable with `model="opus"`.
- Solo brainstorming (no human to answer questions) gracefully proceeds — the brainstorming skill is designed for dialog, but in headless mode Claude must answer its own questions from issue context and proceed without blocking.
