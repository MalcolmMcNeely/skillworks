# The Tracker

Part of [the Dev loop](../the-loop.md).

The **Tracker** is where your team keeps its specs and tickets. `tracker` in `docs/agents/loop.json`
says which one it is. Setup asks you, and writes your answer there. It takes one of two answers.

**`github`**. A spec is a GitHub issue, and each ticket is a sub-issue of it. The loop reads and
writes them with `gh`.

```json
{ "tracker": "github" }
```

Pick `github` when your remote is on GitHub and has Issues turned on. Setup suggests it when `origin`
names `github.com`.

**`files`**. A spec is a folder in `.specs/`, and each ticket is a Markdown file in that folder. They
are committed to your repo, beside your code. The loop reads them with `git` alone, so it needs no
`gh`.

```json
{ "tracker": "files" }
```

Pick `files` when your remote is not on GitHub: GitLab, Bitbucket, or a bare repo on a shared drive.
Setup suggests it when `origin` does not name `github.com`. Any remote works. A repo with no remote
does not: setup stops, and prints the commands that add one.

The rest of this page is about `files`. With `github`, the rest of [the Dev loop](../the-loop.md)
says how the loop uses the issues.

## The `.specs/` folder

```
.specs/
  0007-local-tracker/
    spec.md
    tickets/
      01-read-loop-json.md
      02-close-in-worktree.md
```

Each spec is a folder, `<number>-<slug>`. `/skillworks:to-spec` writes it and pushes it. Its number
is one more than the highest number on the remote. When two specs are written at the same time, the
remote refuses the second push, and that spec takes the next number.

`/skillworks:to-tickets` writes one file for each ticket in `tickets/`. One file for each ticket
means two jobs never edit the same file.

A ticket's number is local to its spec. So a ticket is named by both numbers, `<spec>/<ticket>`:
`7/2` is ticket `02` of spec `0007`. You give the loop the spec's number, as you give it an issue
number: `/skillworks:spec-loop 7`.

## A spec file and a ticket file

Each file is plain Markdown, so you read and edit it in any editor. The frontmatter at the top holds
the state the loop reads. The text below it is what a Session reads.

A spec, `.specs/0007-local-tracker/spec.md`:

```markdown
---
status: open
---

# SPEC: A team without GitHub tracks its specs in committed files

## Problem Statement

A team whose remote is not GitHub cannot use the loop at all.
```

A ticket, `.specs/0007-local-tracker/tickets/02-close-in-worktree.md`:

```markdown
---
status: open
blocked-by: [1]
claimed-by:
---

# TICKET: Close the ticket in the worktree

## What to build

The ticket's Session closes its own ticket, in the same commit as its code.

## Acceptance criteria

- [ ] The close and the code are in one commit.

## Blocked by

- 1
```

| Field | Where | What it holds | Who writes it |
|---|---|---|---|
| `status` | `spec.md` and each ticket | `open` or `closed`. | `to-spec` and `to-tickets` write `open`. The loop closes it. |
| `blocked-by` | Each ticket | The numbers of the tickets in the same spec that must close first. | `to-tickets`. |
| `claimed-by` | Each ticket | The `user.email` of the loop that took the ticket. | The loop. Leave it empty. |
| `branch` | `spec.md`, when `target-branch` says `spec` | The spec's own branch, `spec/<slug>`. | `to-spec`. |

You can edit a file by hand, like any other file. Push the edit to the Target branch, because the
loop reads the files there and not in your checkout.

## A claim and a close

- **Reading.** The loop fetches the Target branch from `origin`, and reads `.specs/` there. So it sees
  what every other loop and every teammate has pushed.
- **Picking.** A ticket can start when it is open, nobody has claimed it, and each ticket in its
  `blocked-by` is closed.
- **Claiming.** The loop sets `claimed-by: <your user.email>` in a commit, and pushes it to the Target
  branch. If the remote refuses the push, another loop moved first. The loop reads again, and claims
  the next free ticket. A lost push race is what stops two loops from taking one ticket.
- **Closing a ticket.** `finish` sets `status: closed` and adds a `## Closing note` at the end of the
  ticket file, in the same commit as the code. The note holds what the Closing note holds on
  GitHub: what was done, which tests prove it, and which checks did not run. The close reaches the
  remote only when the ticket Lands. So a ticket is never closed without its code.
- **Closing the spec.** After the last ticket and the drift check, the loop sets `status: closed` in
  `spec.md` and pushes it. Do not close a spec by hand while a loop runs on it.

With `spec` as your Target branch, the spec's folder sits on `spec/<slug>`. So its pull request
carries the spec and its code together.

## Why `.specs/` is committed

Do not add `.specs/` to `.gitignore`. Each job builds in a worktree of its own, and a worktree cannot
see a gitignored folder of your checkout. A job that cannot see its ticket cannot build it or close
it.

Committed, the files give three things. Every teammate and every loop reads the same state. A claim is
a pushed commit, so it holds. And a close goes in the same commit as its code.
