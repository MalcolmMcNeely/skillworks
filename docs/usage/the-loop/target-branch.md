# The Target branch

Part of [the Dev loop](../the-loop.md).

The **Target branch** is the branch a ticket Lands on. `target-branch` in `docs/skillworks/loop.json`
says which one it is. Setup asks you, and writes your answer there. It takes one of two kinds of
answer.

**A branch name**, such as `main`, `master` or `develop`. That branch is the Target branch for every
ticket of every spec. The loop cuts each Job branch from it, Lands each ticket on it, and pushes to it
straight away. The grill pushes each word and ADR to it as they settle, each ADR in the folder
`adr-folder` names.

```json
{ "target-branch": "main" }
```

Pick a branch name when your team pushes straight to that branch. Your GitHub login must be able to
push to it with no pull request and no status check. The preflight tests this, and stops if the push
would be refused.

**`pr`**, for PR mode. You name the branch and open the pull request. For each spec you name the
spec's branch at the grill, by your team's own rule, and Skillworks makes it on `origin` from your
default branch. That branch is the spec's Target branch. Your team reviews the whole spec as one
pull request from it to your default branch. Your checkout stays on the default branch, so you can
grill and loop many specs at once, as with a branch name.

```json
{ "target-branch": "pr" }
```

Pick `pr` when your default branch is protected, or when your team reviews its work through pull
requests. The preflight checks that the default branch is on the remote, and does not care about its
protection. With `pr`:

- You start the grill on your default branch. Before its first question, the grill asks you to name
  the spec's branch, and runs the `spec-branch` command with that name. Skillworks never checks the
  name against a pattern, so your team's own tools stay the one judge of it.
- `spec-branch` makes the branch on `origin` from your default branch, and opens the grill worktree
  on it, under `.spec-loop/grill/`. It refuses the default branch, a name already on `origin`, and a
  name an open spec holds. The grill then asks you for another name. See
  [When a step fails](stops.md), under A name that cannot hold a spec.
- The grill commits each word and ADR in the grill worktree as they settle, and pushes it to the
  spec's branch at once, so a teammate sees it there. Your checkout never leaves the default branch.
- `/skillworks:to-spec` publishes the spec with that branch as its branch: under `## Branch` with
  `github`, or as `branch` in `spec.md` with `files`. The loop reads it there. Then it removes the
  grill worktree. It opens no pull request.
- Each ticket Lands on your branch exactly as it would on a branch name. Blocking, the push race and
  the Turn work the same. A closed ticket still means its code is on its Target branch.
- After the drift check and the full run, the loop closes the spec, with either Tracker. Its last
  lines tell you to open the pull request from your branch. It marks no pull request ready and never
  merges. A person reviews it and merges it.
- You open the one pull request, from your branch. Skillworks opens none, and you write no closing
  keyword such as `Closes #<spec>` in it.

Every other part of [the Dev loop](../the-loop.md) is the same for both kinds. Where it says the
Target branch, read the branch name you set, or the branch you named at the grill.

## An old `"spec"`

PR mode was called spec mode, and its value was `"spec"`. The loop, the preflight and every script
that reads `target-branch` now refuse `"target-branch": "spec"`, and nothing reads it as `"pr"`. To
go on, write `"target-branch": "pr"` in `docs/skillworks/loop.json`.
