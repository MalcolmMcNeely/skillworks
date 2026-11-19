# A team can make the Full run run only the Touched checks

On a large repo, the Full run after a spec run runs every check, takes a long time, and holds so much
memory that two loops on one machine cannot both run it. The Suite file may hold `"full-run"`, set to
`"all"` or `"touched"`. With `"all"`, the default, nothing changes. With `"touched"`, the Full run
runs only the Touched checks: each check with an input, as its `ignores` say, that changed between
the spec's base commit and the newest Target branch. It still trusts no Proof. The setting sits in
the Suite file because the size of a repo is the same for every developer, and the Suite file is
where a team says what green means.

Every change after the base commit counts, whoever made it, so a teammate's push or a merge into a
long-running branch touches the checks it reaches. The base commit is the Target branch when the
spec's first run started, and never `main`. When no check is touched, the Full run is green, and the
log says that no check ran, because `ignores` is already the team's word on what a check reads.

## Considered options

**The Full run trusts Proofs.** Almost no new code. Rejected: the last ticket's Suite step has
usually proved the same inputs, so the Full run would often run nothing, and it would no longer catch
a stale Proof.

**A check names a command that runs only the tests the changed files reach.** The finest grain,
inside one large check. Rejected for now: each team writes and keeps that command, and a wrong pick
of tests is a green the loop cannot see through. It can come later, as an extra a check may name.

**Only the spec's own commits count.** A smaller run. Rejected: a teammate's change is in the tree
that ships, and a check it broke would be skipped.

## Consequences

This narrows a line in [ADR 0039](0039-the-suite-keeps-proofs-and-a-check-names-what-it-ignores.md),
which turned down an age limit on Proofs because the Full run catches a change outside the repo, such
as a new SDK. Under `"touched"`, only a Touched check catches it. A check no spec touches keeps its
Proof on that machine until someone deletes the Proofs or runs the Full run with `"all"`. CI on a
clean machine still runs everything.
