# Reading a run

Part of [the Dev loop](../the-loop.md).

The log is `.spec-loop/<spec>/loop.log`. Every step's result and error output sits beside it.

```
15:55:20 SHAPE spec #200 holds 14 stories, 6 decisions and 1 Surface, so the drift check's Verdicts can be counted
15:55:22 START #202 TICKET: Preflight checks for uv
15:55:32 STEP  #202 build        2/6
15:57:41 STEP  #202 standards    2/6
15:59:38 EDIT  #202 standards    changed scripts/preflight.py
16:02:18 STEP  #202 fix          2/6
16:29:54 STEP  #202 finish       2/6
16:56:48 ok    #202 landed on master as bfa44a6 in 1 try, holding the Turn for its push
16:56:52 DONE  #202  bfa44a6
16:57:06 STEP  #203 build        3/6  ~245m left
```

The `SHAPE` line comes first. It says the spec is in the counted shape, and how many items it holds.
A spec in another shape gets an `ABORT` line in its place, and nothing after it.

A spec with no tickets gets a `CUT` line after it. The slices the Cut showed follow it, as that
Session wrote them, and then the first `START` line:

```
15:55:21 CUT   spec #200 has no tickets, so a Session cuts them first
1. **Title**: Preflight checks for uv
   **Blocked by**: none
```

The Cut's result and error output sit beside the log as `cut.json` and `cut.err`.

A check that flakes in a ticket's `suite` step, or in its landing, adds a `FLAKE` line that names
the check and the file that keeps its red output:

```
16:27:40 FLAKE #202 suite        dotnet test Skillworks.slnx went red and then passed. Its red output is kept at .spec-loop/200/flake-ticket-202-suite-20260928T162740512804Z.out
```

After the last ticket, the drift check adds its own lines, then the Name check, then the full run:

```
18:31:40 SCOPE the drift check reads 23 commits of spec #200, and leaves out 4 other commits after the base commit
18:31:40 DRIFT all tickets closed. Checking the result against spec #200.
18:40:12 DRIFT the report is recorded on spec #200. Read it at .spec-loop/200/drift.md
18:40:12 COUNT the spec holds 21 items, and the drift report gives 21 Verdicts
18:40:12 NOTE  Unrequested: A helper that trims the log's lines to 80 characters.
18:40:13 SCOPE the Name check reads 23 commits of spec #200, and leaves out 4 other commits after the base commit
18:40:13 NAMES checking the names spec #200 brought in against the glossary.
18:44:02 NAMES the report is recorded on spec #200. Read it at .spec-loop/200/names.md
18:44:02 NAMES no rename is owed on spec #200
18:44:02 FULL  #202, #203 landed in this run, so the whole Suite runs on the newest origin/master with no Proofs and no images
18:52:30 FULL  run 1 passed
18:52:30 FULL  master at 4c1d9e2 passed the whole Suite
18:52:31 END   spec #200 complete. Every ticket is on master.
```

A full run with a Flake names the check, the file that keeps its red output, and the worktree it
leaves:

```
18:52:30 FULL  run 2 passed
18:52:30 FLAKE full-run          dotnet test Skillworks.slnx went red and then passed. Its red output is kept at .spec-loop/200/flake-full-run-20260928T185230204417Z.out
18:52:30 FULL  its worktree is left at .claude/worktrees/spec-200/full-run. The next full run of spec #200 removes it.
18:52:30 FULL  master at 4c1d9e2 passed the whole Suite
```

A `SCOPE` line comes before the drift check, the drift re-check and the Name check. It says how many
of the spec's commits the check reads, and how many other commits after the base commit it leaves
out: a hand commit with no `Ticket:` trailer, or another spec's ticket. The script judges nothing
here. It prints the counts, and the check judges. A spec with no commit to read gets a `STOP` line
in place of the `SCOPE` line, as [When a step fails](stops.md) shows.

The `COUNT` line says how many items the spec holds and how many Verdicts the report gave. A `NOTE`
line names each Unrequested item. A `WARN` line names a Verdict for an item the spec does not hold.

When the count finds a Gap, [the Gap round](drift-check.md#the-gap-round) adds its lines before the full run's. A
`GAP` line names each Gap, and the `FILED` line names the Gap ticket. The ticket's own lines follow,
then the re-check's:

```
18:40:12 COUNT the spec holds 21 items, and the drift report gives 20 Verdicts
18:40:12 GAP   S4 is Missing: No code writes the NOTE lines.
18:40:12 GAP   The user docs has no Verdict
18:40:14 FILED #210 under spec #200 builds 2 Gaps, so the loop goes round once
18:40:15 START #210 TICKET: Build the Gaps the drift check found
19:31:02 DONE  #210  9e3a1f0
19:31:03 SCOPE the drift re-check reads 24 commits of spec #200, and leaves out 4 other commits after the base commit
19:31:03 DRIFT the Gap ticket is closed. Checking S4, The user docs against spec #200 again.
19:39:47 DRIFT the report is recorded on spec #200. Read it at .spec-loop/200/drift-gaps.md
19:39:47 COUNT the re-check was asked about 2 items, and the drift report gives 2 Verdicts
```

When the Name check finds a rename, [the rename ticket](name-check.md#the-rename-ticket) adds its lines before
the full run's. A `NAME` line names each rename, a `NOTE` line names each concept with no glossary
word, and the `FILED` line names the rename ticket. The ticket's own lines follow, then the Name
re-check's:

```
18:44:02 NAME  `Batch`: it now names a whole run of tickets, and the glossary calls that a Job.
18:44:02 NAME  Gap and Hole: two tickets named one owed item two ways, and no glossary word.
18:44:02 NOTE  Gap and Hole has no glossary word, so the rename takes the name the code and the spec use most. A person settles the word.
18:44:04 FILED #211 under spec #200 makes 2 renames, so the loop builds it and checks each one
18:44:05 START #211 TICKET: Make the renames the Name check found
19:20:41 DONE  #211  5b7c2d4
19:20:42 NAMES the rename ticket #211 is closed. Checking it made each rename on spec #200.
19:24:10 COUNT the rename ticket owes 2 renames, and the Name re-check gives 2 Verdicts
19:24:10 NAMES every rename is made on spec #200
```

A `STOP` line names each Gap left after the round, each Contradicts, each rename not made and a spec
with no commit to read, as [When a step fails](stops.md) shows. It comes last, after the
full run's lines, in place of `END`. `END` comes only on [a clean finish](full-run.md#a-clean-finish).

The position counts closed tickets, so a restarted run starts at its real place. The time left is the
mean of the tickets this run has finished, with the one now running counted as still to do.

Expect a long run. A ticket can take from half an hour to a few hours.

`spec-loop <spec> --dry-run` prints the whole plan instead of running it: the `SHAPE` line, every
ticket, its worktree and Job branch, every step's command and facts, the landing steps, and what comes
after the last ticket: the drift check, the Gap round, the Name check, the rename ticket, the Name
re-check and the full run. A spec in another shape stops the dry run at its `ABORT` line, as it would
stop a run. It starts no Session and reaches no remote.

A dry run on a spec with no tickets still checks the shape first. Then it says that a Session would
cut the tickets first, and prints the Cut as the `cut` step. It prints the steps each ticket will
take, with `<ticket>` where the number goes, then the landing steps and what comes after the last
ticket.
