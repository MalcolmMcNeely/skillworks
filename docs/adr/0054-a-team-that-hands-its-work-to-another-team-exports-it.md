# A team that hands its work to another team Exports it

A developer can run the loop in a repo whose team does not use Skillworks, and hand that team work
that holds no trace of it. The loop runs as it always does, trailers, bookkeeping commits and
`.specs/` included, on branches only its own remote sees. Then it Exports what it built onto the
developer's own branch. The team never depends on the Plugin, and it can go on without it when the
developer leaves.

`"export": true` in `docs/agents/loop.json` switches it on, with `target-branch` set to `spec`. It is
off by default. Setup asks whether the work goes to a team that does not use Skillworks. With yes,
it writes the Steering onto a Steering branch, `skillworks/steering`, pushed only to `origin`, and
the developer's own branches never hold a Steering file. With the `files` Tracker, `origin` can be a
remote of the developer's own, such as a bare repo on their machine, and the team never sees the
loop's branches. The `github` Tracker needs `origin` to be the GitHub repo whose Issues it uses, so
when the team lends its own, the Steering branch and the Target branches sit on the team's remote
under `skillworks/`. They never merge, and the team needs nothing to work beside them.

The developer cuts their branch from the default branch and starts the grill on it. When it settles
the first word or ADR, the grill brings the Steering branch onto the commit that branch sits on,
rebasing the Steering commit and pushing it, and stops on a conflict. It then cuts the spec's Target
branch, `skillworks/spec/<their branch>`, from the Steering branch, and opens no pull request. So
every ticket is built and tested against the same code the developer's branch starts from.

The Export runs once, after the full run passes and the spec closes, and before `END`. It writes onto
the developer's branch:

- one commit holding the grill's `Glossary:` and `ADR:` changes, titled by the spec,
- then one commit for each ticket, in the order they Landed, titled by the ticket, found by the
  `Ticket` trailer,
- each with no body and no trailer, and none touching `.specs/` or a file that only a left-out commit
  created, such as `suite.json`.

It lists every commit and every file it left out. When a ticket's change does not apply, it writes
nothing and stops, naming the ticket and the file. It never pushes. The developer pushes the branch
to the team's remote and opens the pull request.

This amends ADR 0036: with `export`, the spec's branch is cut from the Steering branch and not from
the default branch, it is named after the developer's branch, and no pull request is opened from it.

## Considered options

**Switch the trailers, the bookkeeping commits and `.specs/` off at the source.** Rejected. Land, the
drift check and the Name check read the `Ticket` trailer, claims need `.specs/` (ADR 0037), and the
loop would carry a second way of working through every step. ADRs 0031, 0037, 0038 and 0046 would
all be reversed. Only the Session trailer gained a switch, in ADR 0053.

**Export the whole branch, minus a list of Skillworks paths.** Rejected. The list goes stale, and it
removes a change a ticket really made to one of those paths.

**Export after each Land.** Rejected. The loop would write over a branch the developer may already
have pushed, so every push after the first would need a force.

**Hand a conflict to a Session, as Land does.** Rejected. The Session would change code after the
full run proved it, and nothing would prove it again.

**Keep the Steering on the developer's branch, and leave its commit out.** Rejected. The branch would
hold the Steering until the Export, and a push before then hands it to the team.
