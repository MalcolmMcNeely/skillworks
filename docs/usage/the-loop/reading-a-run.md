# Reading a run

Part of [the Dev loop](../the-loop.md).

The log is `.spec-loop/<spec>/loop.log`. Every step's result and error output sits beside it.
Each line starts with the date and the time it was written, in UTC, so the runs of two days in one
log can be told apart. A line that goes on from the line above it, such as a `Denial:` line, has no
date or time of its own.

```
2026-09-28 15:55:20 SHAPE spec #200 holds 14 stories, 6 decisions and 1 Surface, so the drift check's Verdicts can be counted
2026-09-28 15:55:22 START #202 TICKET: Preflight checks for uv
2026-09-28 15:55:32 STEP  #202 build        2/6
2026-09-28 15:57:40 DENY  #202 build        0 Denials
2026-09-28 15:57:41 STEP  #202 standards    2/6
2026-09-28 15:59:37 DENY  #202 standards    1 Denial
      Denial: Bash {"command": "cd scripts && uv run pytest"}
2026-09-28 15:59:38 EDIT  #202 standards    changed scripts/preflight.py
2026-09-28 16:02:18 STEP  #202 fix          2/6
2026-09-28 16:29:50 DENY  #202 fix          0 Denials
2026-09-28 16:29:54 STEP  #202 finish       2/6
2026-09-28 16:56:40 DENY  #202 finish       0 Denials
2026-09-28 16:56:48 ok    #202 landed on master as bfa44a6 in 1 try, holding the Turn for its push
2026-09-28 16:56:52 DONE  #202  bfa44a6
2026-09-28 16:57:06 STEP  #203 build        3/6  ~245m left
```

The `SHAPE` line comes first. It says the spec is in the counted shape, and how many items it holds.
A spec in another shape gets an `ABORT` line in its place, and nothing after it.

A spec with no tickets gets a `CUT` line after it. The slices the Cut showed follow it, as that
Session wrote them, and then the first `START` line:

```
2026-09-28 15:55:21 CUT   spec #200 has no tickets, so a Session cuts them first
1. **Title**: Preflight checks for uv
   **Blocked by**: none
```

The Cut's result and error output sit beside the log as `cut.json` and `cut.err`.

A `DENY` line follows every result a Session returns. It gives the count of Denials in that result,
and lists the first three below it on `Denial:` lines. A Denial is a tool call the Session was not
allowed to make. The line is there when the count is 0 as well, and when the step passed, so a
Session that found a way round a Denial still shows it. A Nudged step has one `DENY` line for each
result. The `suite` step starts no Session, so it has none. The Cut, the drift check and the Name
check name the spec, and the file their result sits in:

```
2026-09-28 15:55:21 DENY  spec #200 cut          5 Denials, and the first 3 follow
      Denial: Write {"file_path": ".claude/rules/words.md", "content": "# Words\n\nThe YAML block at...
      Denial: Bash {"command": "cd docs && git log --oneline"}
      Denial: Bash {"command": "cd docs && git status"}
```

A Session that made a Choice, or named a Hand check, gets a line for each, after its `DENY` line. A
`CHOSE` line holds a Choice and a `HAND` line holds a Hand check. Each names the ticket and the step,
or the spec and the check, and then holds the Session's own line as it wrote it:

```
2026-09-28 15:59:37 CHOSE #202 spec         CHOSE the uv check in preflight.py, because the ticket names no file and the other checks sit there.
2026-09-28 15:59:37 HAND  #202 spec         HAND CHECK run spec-loop on a machine with no uv, and read the ABORT line.
```

When the run ends, the driver writes every Choice and every Hand check of the run again, as one
list after a `LIST` line. It does this at a clean finish, after the `END` line, and at an early stop,
after the `STOP`, `FAIL`, `RED` or `ABORT` line. A run with no Choice and no Hand check has no list:

```
2026-09-28 18:52:31 END   spec #200 complete. Every ticket is on master.
2026-09-28 18:52:31 LIST  this run made 1 Choice and named 1 Hand check
      #202 spec         CHOSE the uv check in preflight.py, because the ticket names no file and the other checks sit there.
      #202 spec         HAND CHECK run spec-loop on a machine with no uv, and read the ABORT line.
```

Each Hand check in the list is a check for you to run. When the loop ends, the Session that started
it names each item in the list to you, one by one.

A check that flakes in a ticket's `suite` step, or in its landing, adds a `FLAKE` line that names
the check and the file that keeps its red output:

```
2026-09-28 16:27:40 FLAKE #202 suite        dotnet test Skillworks.slnx went red and then passed. Its red output is kept at .spec-loop/200/flake-ticket-202-suite-20260928T162740512804Z.out
```

After the last ticket, the drift check adds its own lines, then the Name check, then the full run:

```
2026-09-28 18:31:40 SCOPE the drift check reads 23 commits of spec #200, and leaves out 4 other commits after the base commit
2026-09-28 18:31:40 DRIFT all tickets closed. Checking the result against spec #200.
2026-09-28 18:40:12 DRIFT the report is recorded on spec #200. Read it at .spec-loop/200/drift.md
2026-09-28 18:40:12 COUNT the spec holds 21 items, and the drift report gives 21 Verdicts
2026-09-28 18:40:12 NOTE  Unrequested: A helper that trims the log's lines to 80 characters.
2026-09-28 18:40:13 SCOPE the Name check reads 23 commits of spec #200, and leaves out 4 other commits after the base commit
2026-09-28 18:40:13 NAMES checking the names spec #200 brought in against the glossary.
2026-09-28 18:44:02 NAMES the report is recorded on spec #200. Read it at .spec-loop/200/names.md
2026-09-28 18:44:02 NAMES no rename is owed on spec #200
2026-09-28 18:44:02 FULL  #202, #203 landed in this run, so the whole Suite runs on the newest origin/master with no Proofs and no images
2026-09-28 18:52:30 FULL  run 1 passed
2026-09-28 18:52:30 FULL  master at 4c1d9e2 passed the whole Suite
2026-09-28 18:52:31 END   spec #200 complete. Every ticket is on master.
```

A full run with a Flake names the check, the file that keeps its red output, and the worktree it
leaves:

```
2026-09-28 18:52:30 FULL  run 2 passed
2026-09-28 18:52:30 FLAKE full-run          dotnet test Skillworks.slnx went red and then passed. Its red output is kept at .spec-loop/200/flake-full-run-20260928T185230204417Z.out
2026-09-28 18:52:30 FULL  its worktree is left at .claude/worktrees/spec-200/full-run. The next full run of spec #200 removes it.
2026-09-28 18:52:30 FULL  master at 4c1d9e2 passed the whole Suite
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
2026-09-28 18:40:12 COUNT the spec holds 21 items, and the drift report gives 20 Verdicts
2026-09-28 18:40:12 GAP   S4 is Missing: No code writes the NOTE lines.
2026-09-28 18:40:12 GAP   The user docs has no Verdict
2026-09-28 18:40:14 FILED #210 under spec #200 builds 2 Gaps, so the loop goes round once
2026-09-28 18:40:15 START #210 TICKET: Build the Gaps the drift check found
2026-09-28 19:31:02 DONE  #210  9e3a1f0
2026-09-28 19:31:03 SCOPE the drift re-check reads 24 commits of spec #200, and leaves out 4 other commits after the base commit
2026-09-28 19:31:03 DRIFT the Gap ticket is closed. Checking S4, The user docs against spec #200 again.
2026-09-28 19:39:47 DRIFT the report is recorded on spec #200. Read it at .spec-loop/200/drift-gaps.md
2026-09-28 19:39:47 COUNT the re-check was asked about 2 items, and the drift report gives 2 Verdicts
```

When the Name check finds a rename, [the rename ticket](name-check.md#the-rename-ticket) adds its lines before
the full run's. A `NAME` line names each rename, a `NOTE` line names each concept with no glossary
word, and the `FILED` line names the rename ticket. The ticket's own lines follow, then the Name
re-check's:

```
2026-09-28 18:44:02 NAME  `Batch`: it now names a whole run of tickets, and the glossary calls that a Job.
2026-09-28 18:44:02 NAME  Gap and Hole: two tickets named one owed item two ways, and no glossary word.
2026-09-28 18:44:02 NOTE  Gap and Hole has no glossary word, so the rename takes the name the code and the spec use most. A person settles the word.
2026-09-28 18:44:04 FILED #211 under spec #200 makes 2 renames, so the loop builds it and checks each one
2026-09-28 18:44:05 START #211 TICKET: Make the renames the Name check found
2026-09-28 19:20:41 DONE  #211  5b7c2d4
2026-09-28 19:20:42 NAMES the rename ticket #211 is closed. Checking it made each rename on spec #200.
2026-09-28 19:24:10 COUNT the rename ticket owes 2 renames, and the Name re-check gives 2 Verdicts
2026-09-28 19:24:10 NAMES every rename is made on spec #200
```

A `STOP` line names each Gap left after the round, each Contradicts, each rename not made and a spec
with no commit to read, as [When a step fails](stops.md) shows. It comes last, after the
full run's lines, in place of `END`, and only a `LIST` can follow it. `END` comes only on
[a clean finish](full-run.md#a-clean-finish).

The position counts closed tickets, so a restarted run starts at its real place. The time left is the
mean of the tickets this run has finished, with the one now running counted as still to do.

Expect a long run. A ticket can take from half an hour to a few hours.

`spec-loop <spec> --dry-run` prints the whole plan instead of running it: the `SHAPE` line, every
ticket, its worktree and Job branch, every step's command and facts, the landing steps, and what comes
after the last ticket: the drift check, the Gap round, the Name check, the rename ticket, the Name
re-check and the full run. Last, it prints the paragraph every Session is told after its command. A
spec in another shape stops the dry run at its `ABORT` line, as it would stop a run. It starts no
Session and reaches no remote.

A dry run on a spec with no tickets still checks the shape first. Then it says that a Session would
cut the tickets first, and prints the Cut as the `cut` step. It prints the steps each ticket will
take, with `<ticket>` where the number goes, then the landing steps and what comes after the last
ticket.

## The Journal

A step's result file, such as `ticket-202-standards.json`, holds the newest result of that step. A
Nudge, a second fix or a rerun writes over it. The Journal keeps them all.

The Journal is `.spec-loop/<spec>/journal.jsonl`, beside the log. It has one JSON object on each
line, and each one is an entry for one Session result. The driver adds the entry as the result
comes in, before it acts on the result. It never changes or removes an entry, so a rerun adds new
entries below the old ones. Ticket steps, the Cut, the drift check, the Name check, their re-checks,
and each Nudge of any of them all add entries. The `suite` step starts no Session, so it adds none.

One entry holds:

| Field | What it holds |
|---|---|
| `at` | The date and the time in UTC, as on a log line: `2026-09-28 15:59:37` |
| `ticket` | The ticket number, or `null` for the Cut and the checks |
| `check` | `Cut`, `drift check`, `Name check` or `Name re-check`, or `null` for a ticket step |
| `step` | The step, such as `build` or `standards`, or the name of the Cut or the check, such as `cut` or `drift-gaps` |
| `attempt` | `0` for the first result of the step, `1` and `2` for the answer to the first and the second Nudge |
| `status` | The exit status of the Session |
| `failed` | The checks the result failed. It is `[]` when none failed, and `null` when no check was judged, such as after a non-zero exit |
| `denials` | The count of Denials in the result |
| `blocked` | The Session's `BLOCKED` line, or `null` |
| `choices` | Each `CHOSE` line of the result |
| `hand_checks` | Each `HAND CHECK` line of the result |
| `result` | The whole result as the Session returned it. When it is not JSON, this holds its raw text |

```
{"at": "2026-09-28 15:59:37", "ticket": "202", "check": null, "step": "standards", "attempt": 0, "status": 0, "failed": ["axis-reported"], "denials": 1, "blocked": null, "choices": [], "hand_checks": [], "result": {"is_error": false, "session_id": "...", "result": "I will wait for the tests to finish."}}
```
