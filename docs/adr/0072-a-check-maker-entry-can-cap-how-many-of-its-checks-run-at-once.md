# A Check maker entry can cap how many of its checks run at once

[ADR 0034](0034-the-suite-runs-its-checks-together-and-a-check-can-wait-for-its-paths.md) starts
every check at once, and [ADR 0071](0071-checks-can-share-a-prebuild-and-a-check-maker-prints-them-at-each-run.md)
lets a Check maker print one check per test project. Together they start every test project at once.
A .NET repo with 24 test projects shares one database server among them, and cannot run that wide. A
hand-written check could limit its own width with a flag, but a printed check has no such control.

An entry that holds `checks-from` may hold `max-parallel`, a whole number of 1 or more. No more than
that many of the checks it prints run at the same time. Every other check still starts at once, so a
lint or a front-end test does not wait behind the .NET tests. With no `max-parallel`, nothing changes.
The Suite refuses `max-parallel` on an entry that holds `command`, because a cap on one check means
nothing, and a key that does nothing looks as if it works.

## Considered options

**One cap for the whole Suite file.** Simple, one key. Rejected: the shared resource belongs to the
printed checks, and a cap over every check slows checks that share nothing.

**A cap inside the .NET Check maker.** Rejected: any Check maker that prints many checks has the same
gap, and only the Suite decides when a check starts.

## Consequences

Running the checks together still holds for every check outside a capped entry, and among the checks
inside one up to the cap.
