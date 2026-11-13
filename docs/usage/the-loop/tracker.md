# The Tracker

Part of [the Dev loop](../the-loop.md).

The **Tracker** is where your team keeps its specs and tickets. `tracker` in `docs/skillworks/loop.json`
says which one it is. Setup asks you, and writes your answer there. It takes one of two answers.

**`github`**. A spec is a GitHub issue, and each ticket is a sub-issue of it. The loop reads and
writes them with `gh`.

```json
{ "tracker": "github" }
```

Pick `github` when your remote is on GitHub and has Issues turned on. Setup suggests it when `origin`
names `github.com`.

**`files`**. A spec is a folder in `.specs/`, and each ticket is a Markdown file in that folder. They
live in the Sidecar, and never in your repo. The loop reads them with `git` alone, so it needs no
`gh`, and it pushes nothing but your work to `origin`.

```json
{ "tracker": "files" }
```

Pick `files` when your remote is not on GitHub: GitLab, Bitbucket, or a bare repo on a shared drive.
Pick it too when you want nothing but the work pushed. Setup suggests it when `origin` does not name
`github.com`. Any remote works. A repo with no remote does not: setup stops, and prints the commands
that add one.

The rest of this page is about `files`. With `github`, the rest of [the Dev loop](../the-loop.md)
says how the loop uses the issues.

## The Sidecar

The **Sidecar** is a folder beside the checkout you cloned your repo into. It has the same name,
with `-skillworks` on the end. For a checkout at `C:\code\shop`, it is `C:\code\shop-skillworks`.

- It is a local git repo with no remote. Skillworks makes it with `git init` the first time it needs
  it.
- Each change to it is one commit, made under a lock held in the Sidecar. So `git log` in the Sidecar
  shows what changed, and you can undo a mistake as in any repo.
- It serves one machine. Nothing in it is pushed, so a teammate on another machine does not see your
  specs, and you do not see theirs.
- Every worktree of your repo finds the same Sidecar, beside that first checkout. So every loop
  Session reads the same specs.

The Sidecar is not in your repo, so there is nothing to add to `.gitignore` and nothing that a
gitignored folder could hide from a worktree.

## The `.specs/` folder

```
shop-skillworks/
  .specs/
    0007-local-tracker/
      spec.md
      tickets/
        01-read-loop-json.md
        02-close-in-worktree.md
```

Each spec is a folder, `<number>-<slug>`. `/skillworks:to-spec` writes it. Its number is one more
than the highest of the specs in the Sidecar, and of every spec number the loop's state on this
machine already uses. So a new spec never takes the log or the kept work of an old one. The number is
taken under the lock, so two specs written at the same time get two numbers.

`/skillworks:to-tickets` writes one file for each ticket in `tickets/`.

A ticket's number is local to its spec. So a ticket is named by both numbers, `<spec>/<ticket>`:
`7/2` is ticket `02` of spec `0007`. You give the loop the spec's number, as you give it an issue
number: `/skillworks:spec-loop 7`.

## A spec file and a ticket file

Each file is plain Markdown, so you read and edit it in any editor. The frontmatter at the top holds
the state the loop reads. The text below it is what a Session reads. A Session prints a file with
`tracker-show 7` for a spec, or `tracker-show 7/2` for a ticket, because the Sidecar sits outside its
worktree.

A spec, `.specs/0007-local-tracker/spec.md`:

```markdown
---
status: open
hash: sha256:0c41…
---

# SPEC: A team without GitHub tracks its specs in files

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

# TICKET: Close the ticket in the Sidecar

## What to build

The ticket's Session closes its own ticket with tracker-close.

## Acceptance criteria

- [ ] The ticket is closed with its Closing note.

## Blocked by

- 1
```

| Field | Where | What it holds | Who writes it |
|---|---|---|---|
| `status` | `spec.md` and each ticket | `open` or `closed`. | `to-spec` and `to-tickets` write `open`. The loop closes it. |
| `blocked-by` | Each ticket | The numbers of the tickets in the same spec that must close first. | `to-tickets`. |
| `claimed-by` | Each ticket | The `user.email` of the loop that took the ticket. | The loop. Leave it empty. |
| `branch` | `spec.md`, when `target-branch` says `pr` | The spec's own branch. The loop Lands each ticket there. | `to-spec`. |
| `hash` | `spec.md` | A hash of the spec, so a second run of `to-spec` finds the spec it already wrote and writes none. | `to-spec`. |

You can edit a file by hand, like any other file. Commit the edit in the Sidecar, because the loop
reads what the Sidecar has committed.

## A claim and a close

- **Reading.** The loop reads `.specs/` in the Sidecar. It never fetches from `origin` to find a spec.
- **Picking.** A ticket can start when it is open, nobody has claimed it, and each ticket in its
  `blocked-by` is closed.
- **Claiming.** The loop sets `claimed-by: <your user.email>` in a commit in the Sidecar.
- **Closing a ticket.** `finish` commits the code, and then runs `tracker-close 7/2 <note-file>`. That
  sets `status: closed` and adds a `## Closing note` at the end of the ticket file. The note holds
  what the Closing note holds on GitHub: what was done, which tests prove it, and which checks did
  not run. The close comes before the ticket Lands. If the Land fails, the loop sets the ticket's
  `status` back to `open`, so a ticket is never closed without its code.
- **Closing the spec.** After the last ticket and the drift check, the loop sets `status: closed` in
  `spec.md`. Do not close a spec by hand while a loop runs on it.

The drift report, the Name report and the note that lists a run's Flakes go at the end of `spec.md`
too. A Gap ticket or a rename ticket the loop files is a new ticket file in `tickets/`.

With `pr` as your Target branch, `branch` in the spec's `spec.md` names the branch the loop Lands each
ticket on. The loop closes the spec itself, with either Tracker, so you write no closing keyword such
as `Closes #<spec>` in the pull request.

## Moving from committed `.specs/`

Before the Sidecar, the files Tracker kept `.specs/` committed in your repo. Nothing moves it for you.
To move by hand, from the checkout you cloned:

1. Make the Sidecar, and commit the folder there:

   ```bash
   mkdir ../shop-skillworks
   cp -r .specs ../shop-skillworks/
   git -C ../shop-skillworks init
   git -C ../shop-skillworks add .specs
   git -C ../shop-skillworks commit -m "The specs, moved from the repo"
   ```

   Use your own checkout's name in place of `shop`.

2. Take `.specs/` out of the repo, and push that:

   ```bash
   git rm -r .specs
   git commit -m "The specs live in the Sidecar"
   git push
   ```

3. Remove each ref the old files Tracker pushed to hold a spec number in PR mode, if any:

   ```bash
   git ls-remote origin "refs/skillworks/specs/*"
   git push origin --delete refs/skillworks/specs/<number>
   ```

Move only when no loop runs, because a running loop reads and writes its spec as it goes.
