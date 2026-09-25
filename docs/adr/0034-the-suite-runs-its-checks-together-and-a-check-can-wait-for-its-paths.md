# The Suite runs its checks together, and a check can wait for its paths

The Suite had grown to take most of a ticket. Across spec #237 the `suite` step took a median of 24
minutes, and landing ran it again whenever `main` had moved. The architecture axis ran it too, once
before its review and again after a fix. Most of that time went to one file: the 27 preflight tests,
at about 30 seconds each, proving a script that runs once, when a repo sets the Plugin up.

Two things change.

**The checks run together.** Every repo's Suite starts all its checks at once, after every readiness
command has run one by one. The Suite then takes as long as its slowest check, not the sum of them.
A red check does not stop the others: they all finish, so the `fix` Session reads every failure
rather than the first. The output keeps the order of the Suite file, not the order the checks ended
in, so two runs of one Suite read the same.

**A check can name the paths that wake it.** A check with `when` runs only when the ticket's own
change touches one of those paths: the files that differ from the base its worktree was cut from,
uncommitted work included. At landing it is the same set. A check without `when` always runs, and a
change the loop cannot read runs every check, because running a check that was not needed is the
safe way to be wrong. A check that did not run says so in the Suite output, so the closing comment
names what was not run beside what proved the work.

Here the preflight tests become a check of their own, woken by the script, its short command, its
test, and the shared test support.

The architecture axis no longer runs the Suite at all.
[ADR 0033](0033-a-session-that-stops-short-is-nudged-by-the-driver.md) settled that, and owns it: the
axis runs only the checks the placement-checks file names. Here that is the Architecture tests alone
and the front end's lint. The API tests take six minutes and prove nothing about placement.

## Considered options

**Checks run together only when the Suite file asks.** Safer for a repo whose checks share a build
folder. Rejected: the loop is slow in every repo for the same reason, and a team whose checks
collide can join them into one check.

**A red check stops the others.** Saves minutes on a red Suite. Rejected: a red Suite is rare, the
`fix` Session gets one circuit, and it spends that circuit better knowing every failure.

**A marker only this repo's tests know, turned off by the loop.** Less work. Rejected by
[ADR 0030](0030-steering-is-the-repos-and-machinery-is-the-plugins.md): the Machinery would carry a
fact about one repo's tests. When a check matters is part of what green means, and the Suite file
already says that.

**The change is everything that differs from `origin/main` now.** Rejected: a change that came in on
`main` already passed its own Suite, so it would wake checks the ticket never touched.

**Leave the preflight tests in every Suite and make them cheaper.** Still worth doing, and not
ruled out. It does not answer the question of why a script that runs once is proved on every ticket.

## Consequences

A preflight change is proved only by the ticket that makes it. A change to a file the preflight
reads, and that is not on the list, can break the preflight tests unseen until the next ticket that
wakes them. The list names the shared test support for that reason.

Checks running together share the machine. A check that is fast alone can be slower beside the
others, so the saving is less than the sum of the checks that no longer wait.
