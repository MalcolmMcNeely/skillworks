# The Export

Part of [the Dev loop](../the-loop.md).

The Export is for a developer who works in a team that does not use Skillworks. The team must be able
to go on without the Plugin, so the work they receive holds no trace of it.

The loop runs as it always does, with its trailers, its bookkeeping commits and its Steering, on
branches the team never has to use. When the spec is done, the loop Exports the work onto your own
branch. You push that branch and open the pull request.

## Switch it on

`"export": true` in `docs/agents/loop.json` switches the Export on. It works only with
`"target-branch": "spec"`, because the loop reads the name of your branch from the name of the
spec's Target branch. The preflight and the loop stop when `export` is on with a named Target
branch, and say why. A `loop.json` with no `export` reads as `false`, and the loop runs as it did
before. [Steering](../steering.md) lists the setting.

## The three branches

| Branch | Its name | What it holds |
|---|---|---|
| The Steering branch | `skillworks/steering` | The Steering: `loop.json`, the Suite, the rules and the imports in `CLAUDE.md`. Each Target branch is cut from it. |
| The Target branch | `skillworks/spec/<your branch>` | Everything the loop did for one spec: the grill's words and ADRs, the tickets' commits, the bookkeeping commits and the Steering. |
| The Export branch | Your branch, such as `feature/PROJ-12/slug` | The work alone. You cut it, start the grill on it, and push it when the Export is done. |

The Steering branch and the Target branches live on `origin`. With the `files` Tracker, `origin` can
be a remote of your own, such as a bare repo on your machine, and the team never sees those branches.
With the `github` Tracker, `origin` is the GitHub repo whose Issues the Tracker uses. So when the
team lends its own repo, the Steering branch and the Target branches sit on the team's remote under
`skillworks/`. They never merge, and the team needs nothing to work beside them.

Your branch lives in your checkout. The Export writes onto it there and never pushes it.

## What goes in

The Export runs once, after [the full run](full-run.md) passes and the spec closes, and before `END`.
No Session takes part in it. It reads every commit on the Target branch after the tip of your
branch, and writes onto that tip:

1. One commit holding the grill's changes, when there are any. The grill's commits are the ones
   whose subject starts with `Glossary:` or `ADR:` and that carry no `Ticket` trailer. The commit is
   titled by the spec's title, without `SPEC: `.
2. Then one commit for each ticket, in the order the tickets Landed. A ticket's commits are the ones
   whose `Ticket` trailer names it. Each commit is titled by the ticket's title, without `TICKET: `.

Each Export commit has a subject only: no body and no trailer. Its author is the author of the first
commit it was built from. No Export commit holds a change under `.specs/`.

The Export builds every commit before it moves your branch, and moves it once. When your branch is
checked out, its files move with it.

## What is left out

Every other commit after the tip of your branch is left out: the Steering commit, the bookkeeping
commits, and any commit made by hand.

A file that a left-out commit created, and that does not exist at the tip of your branch, is left out
too. The Suite file is one: the Steering commit created it. When a ticket changed such a file, the
Export leaves that change out of the ticket's commit and keeps the rest. So the Steering can never
come back to your branch through a ticket. A change to a file that exists at the tip of your branch
stays in the ticket's commit.

A ticket whose only changes were under `.specs/`, or in left-out files, gets no commit. Your branch
holds no empty commit.

## What the loop prints

The log gets an `EXPORT` line for each commit the Export wrote, with its hash, its subject and where
it came from. A `LEFT` line counts the commits and the files it left out. Below it, it lists each
commit with its hash and its subject, then each file with the ticket whose change it left out. So you
never lose a hand fix or a change without knowing. Then the `END` line names your branch, and the
lines below it say how to read the branch and how to push it:

```
2026-09-28 18:52:31 EXPORT 7d2e9a1 A developer hands a team work with no trace of it, from the grill
2026-09-28 18:52:31 EXPORT 3b8c0f4 Preflight checks for uv, from #202
2026-09-28 18:52:31 EXPORT a91e5d2 The loop log names each step, from #203
2026-09-28 18:52:31 LEFT  the Export left out 3 commits and 1 file of skillworks/spec/feature/PROJ-12/slug
      5c0e1b7 Steering for a team that does not use Skillworks
      e44f2a9 A hand fix with no trailer
      0b7d3c6 Close spec 200
      docs/agents/suite.json, from #202
2026-09-28 18:52:31 END   spec #200 complete. The Export is on feature/PROJ-12/slug.
      Review it with: git log --oneline 1f0a3c8e5b22..feature/PROJ-12/slug
      Push it with: git push origin feature/PROJ-12/slug
```

With the `github` Tracker the push names `origin`. With the `files` Tracker, `origin` is your own
remote, so the line names `<your team's remote>` in its place.

With `export` on, the loop marks no pull request ready and prints no `PR` line. The only pull request
is the one you open from your branch.
