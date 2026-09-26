# A team without GitHub tracks its specs in committed files

A team whose remote is not GitHub can still split a spec into tickets and run the loop over them.
`tracker` in `docs/agents/loop.json` is `github` or `files`. With `files`, each spec is a folder
under `.specs/`, `<NN>-<slug>/spec.md`, and each ticket a file of its own in its `tickets/` folder,
with frontmatter for its status, its blockers and who claimed it.

`.specs/` is committed, and setup says it cannot be gitignored. Each job builds in a worktree of its
own, and a worktree cannot see a gitignored folder in the main checkout. Committed, a ticket is
closed in the same commit as its code, so it cannot be closed without Landing. A claim is a pushed
commit, so a lost push race is what stops two loops taking the same ticket. And every teammate reads
the same state.

The repo needs a remote, of any kind. Setup refuses a repo with none and says how to add one: a bare
repo on a shared drive is enough.

## Considered options

**Gitignore `.specs/`, so spec text stays out of history.** Rejected. It works for one person on one
machine only. Every job would write outside its own worktree to close its ticket, a close could not
share a commit with its code, and no claim would hold.

**Keep the files for splitting only, and leave the loop on GitHub.** Rejected. It does not let a team
off GitHub run the loop, which is the point.

**Put every ticket in its spec's one file.** Rejected. Two jobs that close two tickets would edit
one file at once, and every landing would meet a conflict.

**Allow a repo with no remote.** Rejected. Worktrees, landing, claims and the grill's push would each
need a second path, and one command gives any team a remote.
