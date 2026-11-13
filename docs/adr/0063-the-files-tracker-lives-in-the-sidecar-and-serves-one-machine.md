# The files Tracker lives in the Sidecar and serves one machine

A developer who uses the files Tracker wants to grill several specs from one checkout and loop them all
at once, and to push nothing to `origin` but the branch the work is on. Committed `.specs/` broke
both: every spec, ticket, claim and report was a commit pushed to the Target branch, and in PR mode a
spec number was held by a ref pushed to `origin`, outside every branch.

So the files Tracker keeps its specs, its tickets and the numbers they take in the Sidecar, a folder
beside the repo named for it with `-skillworks` on the end. It is a git repo with no remote, so each
change keeps its history. The Sidecar is never pushed, so a close and a number are held by a lock in
the Sidecar and not by a push that wins a race.

The Sidecar is on one machine, so the files Tracker serves one machine. Every loop there runs as the
same person, so a claim could never tell two loops apart: the files Tracker keeps no claims, and
`spec-loop` refuses a spec that already has a loop running. ADR numbers are not held anywhere: two
specs grilled at once can take the same one, and the second pull request renumbers its ADR. A team whose specs have to be
seen by more than one person uses the GitHub Tracker. A repo that already holds `.specs/` moves it to
the Sidecar by hand, and nothing migrates it.

This replaces ADR 0037.

## Considered options

**Keep `.specs/` committed with a named Target branch, and use the Sidecar in PR mode only.**
Rejected. Two stores for one Tracker are two paths to build and test, and no one shares files Tracker
specs across machines.

**Hold the numbers on refs pushed to `origin`, as spec numbers were.** Rejected. A team that uses the
files Tracker does so to keep everything but the work off `origin`.

**Hold ADR numbers in the Sidecar.** Rejected. The GitHub Tracker in PR mode has no Sidecar and the
same clash, and a clash is one rename at pull request time.
