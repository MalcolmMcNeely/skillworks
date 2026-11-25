# Sidecar Steering

Part of [the Dev loop](../the-loop.md).

Sidecar Steering is for a developer whose work goes to a team that does not use Skillworks. The team
must be able to go on without the Plugin, so its repo holds no trace of it: no Steering file, no
trailer and no credit for Claude.

The Steering sits in the Sidecar, the folder beside your repo with `-skillworks` on the end of its
name, such as `shop-skillworks` beside `shop`. The Sidecar is a local git repo. It has no remote
unless your team shares its Steering through a
[Steering repo](#share-the-steering-through-a-steering-repo). The Steering being there is what turns the mode on: when the Sidecar
holds `docs/skillworks/loop.json`, every read of a Steering file goes to the Sidecar, and none to the
repo. No setting turns it on, so no setting can disagree with where the Steering sits.

## Steering in both places stops the run

The Steering sits in one place: the repo or the Sidecar. When both the repo and the Sidecar hold
`docs/skillworks/loop.json`, neither copy wins. The preflight stops the run, and names both paths.
Each Session you start warns you, and names both paths, but it still starts.

Remove one of the two. This happens most often when a client takes its Steering from the Sidecar
into its repo: when the repo's copy is the new one, remove the Sidecar's.

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
- A `.gitignore` in the Sidecar that ignores `.specs/` and `landed-commits.tsv`, so a push of the
  Sidecar sends only Steering. An older Sidecar gets it the next time setup runs.

The repo's tracked files never change. [Setup](../setup.md#sidecar-steering) says more.

## Share the Steering through a Steering repo

A team shares its Steering through a Steering repo: a git repo that holds the whole Steering of one
repo. Each member's Sidecar is a clone of it. The Steering repo's URL sits in the Sidecar's own git
remote, so your repo never names it.

Setup asks for the Steering repo's URL right after you answer yes to Sidecar Steering. You can leave
it empty. [Setup](../setup.md#a-steering-repo) says what it does in each case.

### The first member pushes

The first member already has a Sidecar, with the Steering setup wrote. To share it:

1. Make an empty git repo for the Steering, on your team's host or on a shared drive.
2. Run `/skillworks:skillworks-setup`, answer yes to Sidecar Steering, and give the empty repo's URL.
   Setup adds it as the Sidecar's remote, and prints the commands to run next.
3. Commit the Steering in the Sidecar, and push it. With the Sidecar's name in place of
   `shop-skillworks`:

   ```
   cd ../shop-skillworks
   git add --all
   git commit -m "The team's Steering"
   git push -u origin HEAD
   ```

The Sidecar's `.gitignore` keeps `.specs/` and `landed-commits.tsv` out, so the push sends only
Steering. Setup commits and pushes nothing itself.

When the Steering repo already holds a commit, setup stops and writes nothing, because it never
merges two Steerings by guess. Move your local Sidecar away, and run setup again to clone the team's.

### A new member joins

A new member needs one setup run and the Steering repo's URL. With no Sidecar on disk, run
`/skillworks:skillworks-setup`, answer yes to Sidecar Steering, and give the URL. Setup clones the
Steering repo as the Sidecar. It writes none of the team's Steering: it writes only your repo's git
exclude lines and `.claude/settings.local.json`, from the team's settings.

A Sidecar that already has a remote is used as it is.

### When a Session pulls

Each Session you start pulls the Steering repo once, before it loads the rules. The SessionStart hook
runs one fast-forward-only pull in the Sidecar, and only then reads the Sidecar's `CLAUDE.md` and its
imports. So every text in the Session comes from one commit. `/skillworks:grill`,
`/skillworks:implement` and a plain Session all get the newest Steering.

A Sidecar with no remote is not pulled, and the Session says nothing about a pull.

### When a run pulls

A run pulls the Steering repo once, when it starts. `spec-loop` runs the same fast-forward-only pull
in the Sidecar before its preflight reads the Steering. The Sessions of the run pull nothing: the loop
marks each Session it starts, and the hook skips the pull when it sees the mark. So every ticket of the
run reads one commit, even when a teammate pushes while the run goes on.

The run writes the Sidecar's commit to `.spec-loop/<spec>/steering.sha` in your repo, so you can trace
a run's result to the Steering it read. It writes the commit after the pull, and also when the Sidecar
has no remote or the pull failed.

### A failed or slow pull

A failed pull does not stop the Session or the run. The hook or the run stops the pull and gives you one
warning. The warning names the reason, and says that the Steering files on disk are read. The Session
or the run then goes on with those files.

The pull fails when:

- The Steering repo cannot be reached.
- The pull would overwrite an edit you have not committed. Your file on disk loads, so your edit wins
  on your machine until you push it.
- The pull runs past its limit. [The pull's limit](#the-pulls-limit) says how to set it.

### Change the Steering

Use plain git in the Sidecar: edit, commit, push. With the Sidecar's name in place of
`shop-skillworks`:

```
cd ../shop-skillworks
git add docs/skillworks
git commit -m "Add a rule on test names"
git push
```

No Skillworks command commits or pushes the Steering. A skill that writes Steering leaves its edit
uncommitted, so you check it before you push. Each teammate gets the change when they next start a
Session.

### The team's settings

The Sidecar's `.claude/settings.json` holds the team's shared Claude Code settings, and you push it
with the rest of the Steering. When a Session's pull changes that file, the hook merges it into
`.claude/settings.local.json` in the checkout you cloned:

- A key in the shared file wins over the same key in your local file.
- The shared entries join your `permissions.allow` and `permissions.deny`.
- Every entry and key that only your local file holds stays. So the "always allow" rules you clicked
  are kept.

Claude Code reads its settings once, when a Session starts. So a settings change applies from the next
Session, and the hook says so. A pull that does not change the shared settings file merges nothing,
and the hook says nothing about settings.

### The pull's limit

`steering-pull-seconds` in the Sidecar's `docs/skillworks/loop.json` sets how many seconds the pull
can run. When the key is missing, the limit is 30 seconds, so setup does not write it. Raise it on a
slow machine or a slow network:

```json
"steering-pull-seconds": 90
```

The limit must be a whole number from 1 to 240. The preflight stops on any other value, and says why.
Claude Code stops the hook at 300 seconds, so a limit of 240 or less always stops the pull first.

The hook and the run read the limit from the copy of `loop.json` on disk, before the pull. A new limit
that a pull brings applies from the next Session or the next run.

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
