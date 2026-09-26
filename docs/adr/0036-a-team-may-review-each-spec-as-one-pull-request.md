# A team may review each spec as one pull request

Pushing straight to the default branch stays the default, but a team that reviews its work through
pull requests can still run the loop. `target-branch` in `docs/agents/loop.json` says which: a branch
name, such as `main` or `master`, or `spec`. The loop never assumes the default branch is called
`main`, because renaming it is too much to ask of a team that only wants to try the Plugin.

With `spec`, each spec gets a branch of its own, `spec/<slug>`, and one pull request takes the whole
spec to the default branch. That branch is the spec's Target branch: tickets Land on it exactly as
they Land on `main` today, so blocking, the push race and running with nobody watching all carry
over, and a closed ticket still means its code is on the Target branch. The grill creates the branch
and a draft pull request with the first word or ADR it settles, and pushes every later one there.
`to-spec` writes the branch name into the spec, and the loop reads it from there.

This amends ADR 0015 and ADR 0021. A settled word is still pushed the moment it settles, but to the
spec's branch rather than to the default branch. A ticket still Lands the moment it passes, but on
its Target branch.

## Considered options

**One pull request for each ticket.** Deferred, not rejected. The loop would sit idle through every
review, a squash merge drops the Session trailer, and every settled word becomes a pull request of
its own. It can come later as a third value of `target-branch`.

**The grill pushes to the default branch, and only code goes through the pull request.** Rejected.
A team that reviews through pull requests usually protects its default branch, and then every push
from the grill is refused.

**Stacked pull requests.** Rejected. A ticket's blockers form a graph, not a line, so a ticket with
two blockers has no single base.

## Consequences

Two specs in flight can each take the same ADR number, or each edit the same glossary entry. The
second pull request then meets an ordinary merge conflict, and no agent resolves it.

A ticket is closed before its code reaches the default branch. What reaches it is the spec, whole,
when a person merges the pull request.
