# The tickets

Part of [the Dev loop](../the-loop.md).

`/skillworks:spec-loop <spec>` checks that the spec is open, then starts the `spec-loop` script in
the background, and tells you where its log is. The script does the rest. The skill never cuts a
ticket or builds one itself.

The script cuts the tickets as its first step, the **Cut**, after it checks the spec's shape and
before the first ticket, and only when the spec has none. The Cut starts a Session that types
`/skillworks:to-tickets <spec>` and tells it to skip its approval questions, because nobody is at the
terminal to answer them. The slices it shows are written to the loop log, so you can read them while
the work runs. A spec that still has no tickets after the Cut stops the loop with a `STOP` line. A
spec that already has tickets, such as one a restarted run meets, skips the Cut.

Each ticket is a thin slice through every layer, small enough for one fresh Session, and it names the
tickets that must land before it. With `github`, each one is published as a **sub-issue of the
spec**. With `files`, each one is a file in the spec's `tickets/` folder.
Either way, a ticket belongs to one spec, and that is what stops two people's loops from taking each
other's work.

Each Surface in the spec's Surfaces section goes into the ticket whose change needs it. No ticket only
updates a Surface, so every ticket that Lands leaves each Surface in step.

Before the script starts work, it checks that `claude` is on `PATH`, and that the spec is open.
With `github`, it checks that `gh` is logged in. With `files`, it checks that git has a
`user.email`, because it claims each ticket in that name. It records where the Target branch stood
on `origin` in `.spec-loop/<spec>/base.sha`. That file is written once, so a restarted run still
measures from where the first run began.

**Picking a ticket** is a query, not a judgement. The script takes the spec's first open ticket that
has no open blocker and that nobody has claimed.

**Claiming** it, with `github`, assigns itself, waits three seconds, and reads the assignees back.
Another name there means it lets the ticket go and moves on. With `files`, a claim is a pushed commit,
as [the Tracker](tracker.md#a-claim-and-a-close) says.

Open tickets that are all blocked or claimed by someone else stop the run with a `STUCK` line.

## Worktrees and Job branches

Each ticket is built in a worktree of its own, cut from the newest Target branch on `origin`:

| What | Where |
|---|---|
| The worktree | `.claude/worktrees/spec-<spec>/ticket-<n>` |
| The Job branch | `spec-loop/<spec>/ticket-<n>` |

Your own checkout is never worked in. You keep it, on any branch, with any edits in it, for the whole
run. A ticket that Lands has its worktree and its Job branch removed. A ticket that stops keeps both,
so you can read what went wrong.
