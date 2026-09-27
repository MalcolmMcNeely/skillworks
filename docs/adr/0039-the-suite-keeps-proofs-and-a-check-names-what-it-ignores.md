# The Suite keeps Proofs, and a check names what it ignores

The Suite took about 46% of each ticket. Across 56 landed tickets it ran for a median of 17 minutes,
and it ran again at landing whenever `main` had moved. Most checks had no `when`, so they ran on every
ticket. A change that woke no check ran every check, so a docs-only ticket paid the full Suite.

The Suite now keeps a **Proof** each time a check passes: the check, and the exact inputs it passed
on. A check whose inputs match a Proof does not run. A check's inputs are every file in the worktree
that git does not ignore, less the paths the check lists under `ignores`. The Suite reads the tree
as it is, so it no longer reads a diff or a base commit.

- `ignores` replaces `when`. A Suite file that still has `when` is turned down, with a message that
  says how to rewrite it.
- A Suite in which every check has a Proof passes. Its output names each Proof beside what ran.
- Proofs belong to one clone and never leave it. Every worktree and every loop in the clone shares
  them.
- A Proof has no age limit. After each loop run that landed a ticket, a full run on the newest
  `main` trusts no Proof and uses no image. A check that goes red there loses its Proofs, and the
  loop stops and reports.
- A check may name an `image`, a Dockerfile in the repo's Steering. The Suite builds it and runs the
  check inside it, on a copy of every file git does not ignore, so the check sees every file its
  Proof reads.

## Considered options

**Exact `when` lists, held by tests.** Keep the diff and make each list precise, with globs, and a
landing that reruns only checks both sides woke. Easier to explain: this path matched this list.
Rejected because of how each design fails. A path left off a `when` list lets a check sleep, and a
red change lands. A path left off an `ignores` list only runs a check that did not need to run. A
`when` list also needs a line for every file a test reads, and six such hidden reads were found at
once.

**A Proof expires after 24 hours.** It would catch a change outside the repo, such as a new SDK.
Rejected. That change is rare, and the full run after each loop run catches it. A clock only adds
runs that prove nothing new.

**Proofs shared through the remote, as git notes.** A teammate's pass would count here. Rejected. A
Proof holds on the machine that made it, and a pass on one OS proves nothing on another.

**A Suite that ran nothing cannot pass.** [ADR 0034](0034-the-suite-runs-its-checks-together-and-a-check-can-wait-for-its-paths.md)
held this, to guard against a `when` list that missed a path. A Proof is a real pass on the same
inputs, so the guard has nothing left to guard.

## Consequences

This replaces the `when` half of ADR 0034, and the rule that a change that wakes no check runs every
check. Running the checks together still holds.

This repo's Suite file sets `runs` to 1. [ADR 0026](0026-the-driver-runs-the-suite-and-a-red-one-goes-round-once.md)
asked for 2, because the container tests flaked. Across 56 landed tickets, a second run never turned
a red Suite green.

A red circuit, a landing after a rebase and a lost push race now run only the checks whose inputs
are new. Most landings run nothing.

An agent may run the Suite with `skillworks-suite`, and the Proofs it writes count for the driver, so
an agent that checks its own work does not cost the ticket twice.
