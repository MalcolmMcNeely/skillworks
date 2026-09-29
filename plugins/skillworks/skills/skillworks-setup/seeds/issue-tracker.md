# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. The skills write both Trackers through `tracker-publish`, one command for each write, and read with the `gh` CLI.

Infer the repo from `git remote -v` — `gh` does this by itself inside a clone.

`tracker` in `docs/agents/loop.json` names the Tracker. With `github`, read on. With `files`, specs and tickets are committed files and nothing calls `gh`: "The files Tracker", below, takes the place of every GitHub call and convention in this file. "The ticket shape" holds for both.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for a multi-line body.
- **Read an issue**: `gh issue view <number> --comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, with `--label` and `--state` filters.
- **Comment**: `gh issue comment <number> --body "..."`
- **Label**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..." --reason completed`. One call, so a guardrail cannot leave a half-applied state.

## When a skill says "publish to the issue tracker"

Run the `tracker-publish` command the skill gives. It writes to either Tracker.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## The ticket shape

Used by `/skillworks:to-tickets`. This is the team's taste in tickets, so edit it to fit how the team works.

- **Size**: each ticket fits in a single fresh context window.
- **Title**: every ticket title begins with "TICKET:".
- **Paths**: avoid specific file paths or code snippets, because they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim it to the decision-rich parts.
- **Body**: every ticket uses this template.

```markdown
## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective — not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- A reference to each blocking ticket, or "None — can start immediately".
```

## Spec loop operations

Used by `/skillworks:to-tickets`, `/skillworks:implement`, `/skillworks:spec-drift`, `/skillworks:spec-names`, the `spec-loop` command and the `spec-commits` command.

A **spec** issue is the parent. Its **tickets** are GitHub sub-issues of it. That parentage scopes the loop: a driver reads one spec's children and nothing else, so two people running the loop on two specs cannot take each other's tickets.

Read everything through `gh api`. The `gh` flags for sub-issues and dependencies only arrived in gh 2.94.0; `gh api` works on every version. The skills make no write below by hand: `tracker-publish` makes them, and the calls are here so a person can check what it did.

- **The numeric database id.** Both write endpoints below take an issue's numeric `id` — not its `#number`, and not its `node_id`. `gh issue view --json id` hands you the node id, which they reject. Get the right one with `gh api repos/<owner>/<repo>/issues/<n> --jq .id`.
- **Make a ticket a child of a spec**: `gh api --method POST repos/<owner>/<repo>/issues/<spec>/sub_issues -F sub_issue_id=<ticket-db-id>`. Limits: 100 sub-issues per parent, 8 levels of nesting.
- **List a spec's tickets**: `gh api --paginate repos/<owner>/<repo>/issues/<spec>/sub_issues`.
- **Find a ticket's spec**: `gh api repos/<owner>/<repo>/issues/<n> --jq .parent_issue_url`.
- **Add a blocking edge** ("A blocks B"): POST to **B's** `blocked_by` with **A's** id — `gh api --method POST repos/<owner>/<repo>/issues/<B>/dependencies/blocked_by -F issue_id=<A-db-id>`. There is no `blocking` write endpoint; the asymmetry is deliberate. Limit 50 per relationship type.
- **Is a ticket startable?** `gh api repos/<owner>/<repo>/issues/<n> --jq '.issue_dependencies_summary.blocked_by'`. That field counts **open** blockers only, so `0` means go. Do not count the `dependencies/blocked_by` list instead — it includes closed blockers.
- **Claim a ticket**: `gh issue edit <n> --add-assignee @me`, then pause and read the assignees back. There is no compare-and-swap anywhere on the Issues API, so two claims can both succeed. Reading back detects the race; nothing prevents it.
- **Write a spec**: `tracker-publish spec <slug> <file>`, with the spec's branch last in `spec` mode. The file opens with `# SPEC: <title>`. The command files one issue with that title, the text below the heading as its body and the `ready-for-agent` label, and prints its number and URL. In `spec` mode it writes the `## Branch` section from the branch named. It first looks for an open `ready-for-agent` issue with the same title and prints that one instead, so a rerun files no second spec. `/skillworks:to-spec` says how.
- **Write a spec's tickets**: `tracker-publish tickets <spec> <file>...`, every file at once, the same files as with the files Tracker. It files each ticket blockers first as an issue with the `ready-for-agent` label, makes it a sub-issue of the spec, adds a blocking link for each ticket its `blocked-by` names, and prints each issue number. The issue body is the text below the ticket's `# ` heading, with no frontmatter. A rerun matches each file to an open sub-issue by title, files only what is missing and adds only the missing links, so two tickets with one title are turned down. `/skillworks:to-tickets` says how.
- **Record a drift report**: `tracker-publish drift <spec> <file>`. The file opens with `## Drift report`, and the command posts it as a new comment on the spec issue and prints the comment's URL. A rerun adds another comment and leaves the old one, since the loop reads the last comment. `/skillworks:spec-drift` says how.
- **Record a Name report**: `tracker-publish names <spec> <file>`. The file opens with `## Name report`, and the command posts it as a new comment on the spec issue, as for a drift report. `/skillworks:spec-names` says how.
- **Never use `is:blocked` in search** without `-f advanced_search=true`. On the legacy path it silently degrades to a free-text match on the word "blocked" and returns confident nonsense.

Sub-issues carry **no** blocking semantics. A spec with open children is not reported as blocked. Ordering comes from the dependency edges alone.

### Two conventions the loop leans on

These are load-bearing. The loop lands each ticket on its Target branch the moment it finishes, and it finds the ticket a commit belongs to, and the reason behind it, from these two alone.

- **A commit names its ticket.** In the loop, the Plugin's `PreToolUse` hook adds the `Ticket` trailer to every commit a loop Session makes, from the ticket the loop handed that Session, so no model types it. A hand commit still types it: put `Ticket: #<n>` in the message's trailer block — the last paragraph, held off the body by one blank line. Any other trailer sits beside it inside that same block with no blank line between them. Git reads the last paragraph and no earlier one, so a trailer stranded above a blank line is not a trailer.
  - **Read it back**: `git log -1 <commit> --format='%(trailers:key=Ticket,valueonly)'`. That is the whole lookup — no tracker call, no search.
  - **It scopes a spec's checks.** The drift check and the Name check read only the commits whose `Ticket:` trailer names one of the spec's tickets, and never a commit with no trailer. A hand fix that should count for a spec carries `Ticket: #<n>` for one of its tickets.
  - Never use `Closes #<n>`, `Fixes #<n>` or `Resolves #<n>`. Those close the issue the moment the commit lands on the Target branch, and an auto-closed issue carries no Closing note.
- **A ticket is closed with a comment.** `gh issue close <n> --comment "..." --reason completed`. The comment names the commit, what was done and which tests prove it. It is the richest source of intention in the repository, and skills read it back.

A commit also names the Session that made it, though the loop leans on none of it. The Plugin's `PreToolUse` hook adds `Skillworks-Session: <id>` to every `git commit` Claude runs through the Bash or PowerShell tool, in the same trailer block as `Ticket:`. The id is the Session's `session.id`. A commit that more than one Session wrote, such as an amend by a second Session or a Keep of a stopped run, carries one line for each of them. A commit a person makes outside Claude carries none, and Land never asks for one.

- **Read it back**: `git log -1 <commit> --format='%(trailers:key=Skillworks-Session,valueonly)'`. Each line is one Session.
- **Take the id** to the Stores, where it is the `session.id` on every event that Session sent, or to `claude --resume <id>` on the machine that made the commit. The resume works only there, because the Session's history lives on that machine.

## The files Tracker

Used when `tracker` in `docs/agents/loop.json` says `files`. Each spec is a folder under `.specs/`, and each ticket a Markdown file of its own in that folder's `tickets/`:

```
.specs/
  0007-local-tracker/
    spec.md
    tickets/
      01-read-loop-json.md
      02-close-in-worktree.md
```

`.specs/` is committed, and it is never gitignored. Each job builds in a worktree of its own, and a worktree cannot see a gitignored folder.

### A spec and its tickets

Each file opens with frontmatter. A ticket's body follows "The ticket shape".

```markdown
---
status: open
blocked-by: [1]
claimed-by:
---

# TICKET: Close the ticket in the worktree
```

- **`status`**: `open` or `closed`, on `spec.md` and on each ticket.
- **`blocked-by`**: the numbers of the tickets in the same spec that this one waits for.
- **`claimed-by`**: the `user.email` of the loop that took the ticket. The loop sets it. Leave it empty.
- **`branch`**: on `spec.md` alone, when `target-branch` says `spec`. It names the spec's own branch.

A ticket's number is local to its spec, so a ticket is named by both: `<spec>/<ticket>`, such as `7/2` for ticket `02` of spec `0007`. The loop hands each Session its ticket in that form, as in `/skillworks:implement 7/2 --finish`.

- **Read a ticket**: its file, on the remote's Target branch. `git fetch origin <target>`, then `git show origin/<target>:.specs/<spec-folder>/tickets/<ticket-file>`. Inside a loop's worktree, read the file in the worktree, which is where the ticket is closed.
- **Find a ticket's spec**: the folder its file sits in.
- **Write a spec**: `tracker-publish spec <slug> <file>`, with the spec's branch last in `spec` mode. It numbers the spec one above the highest number on the remote, writes the frontmatter and pushes the folder. `/skillworks:to-spec` says how.
- **Write a spec's tickets**: `tracker-publish tickets <spec> <file>...`, every file at once. `/skillworks:to-tickets` says how.
- **Is a ticket startable?** It is open, and every ticket in its `blocked-by` is closed on the remote's Target branch.
- **List what is open**: each spec folder in `.specs/` on the remote's Target branch whose `spec.md` says `status: open`, and in each one the tickets that are startable. `git ls-tree --name-only origin/<target> .specs/` lists the folders. In `spec` mode each spec sits on a branch of its own, so `git fetch origin`, and look on every branch for a spec folder whose `spec.md` names that branch as its `branch`.
- **Record a drift report**: `tracker-publish drift <spec> <file>`. The file opens with `## Drift report`, and the command puts it at the end of the spec's `spec.md` in place of any earlier one, since there is no issue to comment on. The loop reads it back from there. `/skillworks:spec-drift` says how.
- **Record a Name report**: `tracker-publish names <spec> <file>`. The file opens with `## Name report`, and the command puts it below the drift report in place of any earlier one. A new drift report takes it away, since a new drift check starts the judging again. `/skillworks:spec-names` says how.
- **Claim a ticket**: the loop does it, with a commit that sets `claimed-by`, pushed to the Target branch. A push the remote turns down lost a race, so the loop reads again and takes another ticket.

### The two conventions, with files

These stand in for the two above.

- **A commit names its spec and its ticket.** Put `Ticket: <spec>/<ticket>` in the message's trailer block, such as `Ticket: 7/2`, in the same trailer block as any other. Read it back the same way: `git log -1 <commit> --format='%(trailers:key=Ticket,valueonly)'`. A spec's checks read only the commits whose trailer names one of its tickets, and never a commit with no trailer, so a hand fix that should count for a spec carries `Ticket: <spec>/<ticket>` for one of its tickets.
- **A ticket is closed in the commit that holds its code.** Before you commit, set `status: closed` in the ticket's frontmatter, and add a `## Closing note` section at the end of its file. The note holds what the Closing note holds on GitHub, where it is the comment the ticket closes with: what was done, which tests prove it, which checks did not run, and any finding left unfixed with the reason. It cannot name its own commit, and it has no need to. Commit the note with the code, and push nothing. The close reaches the remote only as the ticket Lands, so a ticket whose Land fails is never closed there. Skills read the note back.
- **A spec is closed by its loop.** After the last ticket and the drift check, the loop sets `status: closed` in `spec.md` on the Target branch. Never close it by hand while a loop runs on it.
