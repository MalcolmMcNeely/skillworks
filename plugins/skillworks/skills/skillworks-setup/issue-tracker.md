# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. Use the `gh` CLI for everything.

Infer the repo from `git remote -v` — `gh` does this by itself inside a clone.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for a multi-line body.
- **Read an issue**: `gh issue view <number> --comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, with `--label` and `--state` filters.
- **Comment**: `gh issue comment <number> --body "..."`
- **Label**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..." --reason completed`. One call, so a guardrail cannot leave a half-applied state.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Spec loop operations

Used by `/skillworks:to-tickets`, `/skillworks:implement`, `/skillworks:spec-drift` and `scripts/spec_loop.py`.

A **spec** issue is the parent. Its **tickets** are GitHub sub-issues of it. That parentage scopes the loop: a driver reads one spec's children and nothing else, so two people running the loop on two specs cannot take each other's tickets.

Write everything through `gh api`. The `gh` flags for sub-issues and dependencies only arrived in gh 2.94.0; `gh api` works on every version.

- **The numeric database id.** Both write endpoints below take an issue's numeric `id` — not its `#number`, and not its `node_id`. `gh issue view --json id` hands you the node id, which they reject. Get the right one with `gh api repos/<owner>/<repo>/issues/<n> --jq .id`.
- **Make a ticket a child of a spec**: `gh api --method POST repos/<owner>/<repo>/issues/<spec>/sub_issues -F sub_issue_id=<ticket-db-id>`. Limits: 100 sub-issues per parent, 8 levels of nesting.
- **List a spec's tickets**: `gh api --paginate repos/<owner>/<repo>/issues/<spec>/sub_issues`.
- **Find a ticket's spec**: `gh api repos/<owner>/<repo>/issues/<n> --jq .parent_issue_url`.
- **Add a blocking edge** ("A blocks B"): POST to **B's** `blocked_by` with **A's** id — `gh api --method POST repos/<owner>/<repo>/issues/<B>/dependencies/blocked_by -F issue_id=<A-db-id>`. There is no `blocking` write endpoint; the asymmetry is deliberate. Limit 50 per relationship type.
- **Is a ticket startable?** `gh api repos/<owner>/<repo>/issues/<n> --jq '.issue_dependencies_summary.blocked_by'`. That field counts **open** blockers only, so `0` means go. Do not count the `dependencies/blocked_by` list instead — it includes closed blockers.
- **Claim a ticket**: `gh issue edit <n> --add-assignee @me`, then pause and read the assignees back. There is no compare-and-swap anywhere on the Issues API, so two claims can both succeed. Reading back detects the race; nothing prevents it.
- **Never use `is:blocked` in search** without `-f advanced_search=true`. On the legacy path it silently degrades to a free-text match on the word "blocked" and returns confident nonsense.

Sub-issues carry **no** blocking semantics. A spec with open children is not reported as blocked. Ordering comes from the dependency edges alone.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: one issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a sub-issue, by the call above. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, assigned to the driving dev.
- **Blocking, frontier query, claim**: as in "Spec loop operations". A ticket is unblocked when every blocker is closed.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer to the map's Decisions-so-far.
