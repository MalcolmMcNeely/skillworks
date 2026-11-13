# Sidecar Steering

Part of [the Dev loop](../the-loop.md).

Sidecar Steering is for a developer whose work goes to a team that does not use Skillworks. The team
must be able to go on without the Plugin, so its repo holds no trace of it: no Steering file, no
trailer and no credit for Claude.

The Steering sits in the Sidecar, the folder beside your repo with `-skillworks` on the end of its
name, such as `shop-skillworks` beside `shop`. The Sidecar is a local git repo with no remote,
so nothing in it is ever pushed. The Steering being there is what turns the mode on: when the Sidecar
holds `docs/skillworks/loop.json`, every read of a Steering file goes to the Sidecar, and none to the
repo. No setting turns it on, so no setting can disagree with where the Steering sits.

## Turn it on

Run setup, with `/skillworks:skillworks-setup`. Its first question asks whether the work goes to a
team that does not use Skillworks. Answer yes. Setup then writes:

- Every Steering file into the Sidecar, under `docs/skillworks/`, with `loop.json` set to PR mode
  and the files Tracker.
- The Sidecar's `CLAUDE.md`, with the `## Agent skills` block and its imports.
- The Sidecar's `.claude/settings.json`, which the loop hands to every Session, and the same settings
  in `.claude/settings.local.json` in the checkout you cloned, for the sessions you start yourself.
- The working folders and `.claude/settings.local.json` in your repo's git exclude file,
  `.git/info/exclude`, and never in `.gitignore`.

The repo's tracked files never change. [Setup](../setup.md#sidecar-steering) says more.

## It needs PR mode and the files Tracker

- **PR mode.** `target-branch` is `pr`. For each spec the grill asks you to name a branch, Skillworks
  makes it on `origin`, and the loop Lands each ticket straight on it. Name it by your team's own
  rule, such as `feature/PROJ-12/slug`. When the loop ends, open the one pull request from it, the
  way your team's host does. [The Target branch](target-branch.md) says more.
- **The files Tracker.** `tracker` is `files`. The specs and tickets sit in the Sidecar, so no issue
  on your team's GitHub shows Skillworks. [The Tracker](tracker.md) says more.

Setup refuses the GitHub Tracker in this mode. The preflight stops with any other `target-branch` or
`tracker`, and says which one to write.

## Commits carry no trailer

No commit the loop or Claude makes carries a `Ticket` trailer, a `Skillworks-Session` trailer or a
credit line for Claude. The Plugin's hook adds none, and refuses a credit line the model typed. The
settings setup writes turn Claude Code's own credit off.

The loop still needs to know which commits are a ticket's. Each time a ticket Lands, it adds the
ticket's commits to a list in the Sidecar, `landed-commits.tsv`. The landing, the drift check, the
Name check and `review-changes` read that list where they read the trailer before. A commit you make
by hand is in no list, so it counts toward no ticket.

## The loop stops when the branch is rewritten under it

Before the loop reads the list, it checks that every commit the list holds is still on the spec's
branch on `origin`. When you rebase, squash or force-push that branch, a listed commit is gone, and
the loop cannot tell which commits are a ticket's. It guesses none: it stops, and names the branch
and the commit. Put the commit back on the branch, or take its line out of the list, and run again.
[When a step fails](stops.md) shows the line.

Rewrite the branch after the loop ends, if your team asks for it, and not while a loop runs on it.

## Move from a Steering branch by hand

Skillworks used to keep this Steering on a branch of its own, `skillworks/steering`, and Export each
finished spec onto your branch. That is gone, and nothing moves it for you. To move:

1. Finish each spec that still runs on a `skillworks/spec/<your branch>` branch, or drop it. The loop
   no longer reads those branches.
2. Copy the Steering from the old branch into the Sidecar. From the checkout you cloned, with the
   Sidecar's name in place of `shop-skillworks`:

   ```
   git fetch origin
   mkdir -p ../shop-skillworks
   git archive origin/skillworks/steering docs/skillworks CLAUDE.md | tar -x -C ../shop-skillworks
   ```

3. In the Sidecar's `docs/skillworks/loop.json`, set `target-branch` to `pr` and `tracker` to
   `files`. An `export` key left there is ignored.
4. Run `/skillworks:skillworks-setup` again, and answer yes. It merges the newer Seeds with your
   team's edits, and writes the settings.
5. Delete the old branches on `origin`, such as `git push origin --delete skillworks/steering`, and
   each `skillworks/spec/` branch you no longer need.

Specs and tickets do not move with the Steering. With the files Tracker kept in committed `.specs/`,
[the Tracker](tracker.md#moving-from-committed-specs) says how to move them.
