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
- **Cleanup on error:** before printing the failure sentinel, leave the working tree clean. If you created `docs/superpowers/specs/` or `docs/superpowers/plans/` artifacts during a failed run, remove them: `git clean -fd docs/superpowers/specs docs/superpowers/plans && git checkout -- .`. Do NOT commit on failure.
