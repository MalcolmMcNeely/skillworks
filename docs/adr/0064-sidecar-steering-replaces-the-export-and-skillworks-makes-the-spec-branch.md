# Sidecar Steering replaces the Export, and Skillworks makes each spec's branch

PR mode and the Export held one spec at a time in one checkout. The developer made a branch by hand,
and the grill wrote on the branch the checkout was on. With the Export, the grill also rebased the one
Steering branch and switched the checkout to a Target branch cut from it, so two specs fought over
both. A team that pushes to `main` grills several specs from it and loops them all at once, and PR
mode could not.

So in PR mode the grill starts on the default branch and asks the developer to name the spec's branch.
Skillworks makes that branch on `origin`, from the default branch, and writes each word and ADR to it
in a worktree of its own, so the checkout never leaves the default branch. The loop Lands every
ticket on that branch, and the developer opens the one pull request from it. The developer still
names the branch, so the team's branch rule still wins.

The Export becomes Sidecar Steering. The Steering sits in the Sidecar, and its being there, not a
setting, is what turns the mode on. With nothing of Skillworks in the repo, nothing is left to strip,
so tickets Land straight on the spec's branch on the team's own `origin`, and the Steering branch, the
`skillworks/spec/<branch>` Target branch, `cut-target-branch` and the Export step all go. A commit
there still carries no trailer, so the loop keeps the list of each ticket's commits in the Sidecar,
and stops rather than guesses when the developer has rewritten the branch under it. Sidecar Steering
needs the files Tracker, because GitHub issues are a trace of Skillworks the team would see.

This replaces ADR 0054, ADR 0056 and ADR 0058, and amends ADR 0057 and ADR 0059. A repo that holds a
Steering branch moves the Steering to the Sidecar by hand, and nothing migrates it.

## Considered options

**Keep the Export step, and move only the Steering to the Sidecar.** Rejected. Once the specs and the
Steering are both in the Sidecar, the only thing the Export still did was fold each ticket's commits
into one, and a team can squash at merge.

**Keep the `Ticket:` trailer on the team's branch.** Rejected. It is the one trace of Skillworks left
in the work, and the Sidecar already holds what only the loop needs.

**Keep the words and ADRs in the Sidecar until the loop runs.** Rejected. A teammate would see no
settled word until the pull request, and a copy step would let the Sidecar and the branch drift.
