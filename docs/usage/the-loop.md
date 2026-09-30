# The Dev loop

How a design becomes code in your repo. The Dev loop has two stages, and one gate between them.

Stage one is an interview. You argue the design out with a Session, and the words and decisions are
written to your repo as they settle. It ends when you confirm the design.

Stage two is a script. It breaks the design into tickets and takes each one to your Target branch on
its own, in a worktree of its own, through a fixed run of Claude Code Sessions. Nobody watches it.

```mermaid
flowchart TD
    grill["The grill<br/>argue the design out"] --> gate{"You confirm?"}
    gate -- no --> grill
    gate -- yes --> spec["The spec"]
    spec --> tickets["The tickets"]
    tickets --> steps["The steps of one ticket"]
    steps --> land["Landing"]
    land -- "another open ticket" --> steps
    land -- "the last ticket" --> checks["The checks at the end<br/>drift check, Name check, full run"]
    checks --> finish(["The finish"])
```

Your `yes` at the gate is the whole of your consent. Nothing between it and the drift report at the
end asks you anything, unless the loop stops.

## The pages of the loop

Each page below holds one part of the loop, in the order a run takes them.

| Page | What it answers |
|---|---|
| [The Target branch](the-loop/target-branch.md) | Which branch a ticket Lands on, and how to choose between a branch name and `spec`. |
| [The Tracker](the-loop/tracker.md) | Where your specs and tickets live, and how the `files` Tracker keeps them in `.specs/`. |
| [Stage one: settle the design](the-loop/the-grill.md) | What the grill asks, what your yes at the gate consents to, and the shape of the spec it publishes. |
| [The tickets](the-loop/tickets.md) | How the Cut makes the tickets, how a ticket is picked and claimed, and where it is built. |
| [The steps of one ticket](the-loop/steps.md) | What is done to a ticket before it Lands, from `build` to `finish`, and how the Suite runs. |
| [Rebasing and Landing](the-loop/landing.md) | How a ticket reaches the Target branch: the rebase, the push race and the Turn. |
| [The drift check](the-loop/drift-check.md) | How the finished work is judged against the spec: the Verdicts, the count and the Gap round. |
| [The Name check](the-loop/name-check.md) | How the names the spec brought in are judged: the Name report, the rename ticket and the Name re-check. |
| [The full run](the-loop/full-run.md) | What the whole Suite proves once the checks at the end are done, and what has to be true before the loop writes `END`. |

## When a step fails

```mermaid
flowchart TD
    step["A step ends"] --> ran{"Session could run?"}
    ran -- no --> stop(["Stop: FAIL line"])
    ran -- yes --> checks{"Facts pass?"}
    checks -- yes --> next(["Next step"])
    checks -- "work still owed" --> nudges{"Two Nudges sent?"}
    nudges -- no --> nudge["Nudge<br/>resume and name what is owed"] --> checks
    nudges -- yes --> stop
    stop --> denial{"Denials listed?"}
    denial -- yes --> bypass["Hint: rerun with --bypass"]
    denial -- no --> rerun["Rerun: Keep, then build again"]
    bypass --> rerun
```

**A Nudge.** A Session can stop before its work is done: no report written, nothing committed, the
ticket still open. The script then resumes that same Session and names what is still owed, so it
carries on with what it knows. Two Nudges are the limit. A step that still owes work after them stops
the loop. A Session that could not run at all, such as one that ended in an error or never loaded its
command, gets no Nudge. It stops the loop at once.

**A stop.** Every other failure stops the run where it stands. The one rescue is the round a red Suite
goes, in [the Suite](the-loop/steps.md#the-suite). The script reopens the ticket, because `finish` may have closed it before its work
reached the Target branch, and the loop only picks open tickets. If this run landed a ticket before
the stop, [the full run](the-loop/full-run.md) runs next. The `FAIL` line in the log names the worktree and the files to read:

```
FAIL  #203 step fix failed check ticket-open. Its worktree is at .claude/worktrees/spec-200/ticket-203. See ...
```

**A spec in another shape.** Before any ticket, the script reads the spec's [counted
shape](the-loop/the-grill.md#the-spec). A spec it cannot count stops the loop there, before a
ticket is claimed or a Session started. The `ABORT` line names each fault. Fix the spec on the
Tracker and run the loop again:

```
ABORT spec #200 is not in the shape the loop counts, so no ticket was started.
      Fault: ## User Stories skips 3: it goes from 2 to 4
      Fault: a Surface item under ## Surfaces opens with no bold name: - The README: says so.
      /skillworks:grill writes a spec in the shape the loop counts. Write it in that shape, and run the loop again.
```

**A rule with no import.** Before any ticket, and before a dry run prints its plan, the script checks
that `CLAUDE.md` imports each rule in `docs/agents/rules/`. It reads both from the repo's top level.
A rule with no import would not load into any step, so the loop stops. The `ABORT` line names the
rule and the line to add. It is the same check, and the same words, as setup's preflight:

```
ABORT docs/agents/rules/words.md has no import in CLAUDE.md, so it does not load into a session. Add this line to CLAUDE.md: @docs/agents/rules/words.md
```

**A missing Steering file.** Before any ticket, and before a dry run prints its plan, the script checks
that each file setup seeds is in the repo. It reads the same list of files that setup writes from, so
a Seed that a newer Plugin adds is checked too. A step that needs a missing file would stop in the
middle of a ticket, so the loop stops first. The `ABORT` line names the file and says to run setup,
which writes the file again:

```
ABORT docs/agents/review-standards.md is missing, and setup seeds it. Run /skillworks:skillworks-setup to write it again.
```

**A spec with no commit to read.** Before the drift check, the drift re-check and the Name check, the
script looks up the spec's commits the way `spec-commits` does. Every Landed ticket's commit names its
ticket in a `Ticket:` trailer, so a spec with no such commit after the base commit means the lookup
broke. The loop stops with a `STOP` line and runs no check, so a broken lookup never reads as a clean
report. The spec stays open, and the full run still runs first:

```
STOP  spec #200 has no commit after the base commit 7c41e0a9d2f3b8c56e1a4d7f09b2c3e8a5d6f1b4 whose Ticket: trailer names one of its tickets. Every Landed ticket's commit names it, so the lookup broke. The drift check did not run and the spec stays open.
```

Check that `git log` on the Target branch shows each Landed ticket's `Ticket:` trailer, and run the
loop again.

**A drift report that leaves work owed.** After the last ticket, the script [counts the drift
check's Verdicts](the-loop/drift-check.md#the-count). No report, a report with no `### Verdicts` list, or a Contradicts
stops the loop with a `STOP` line, and the spec stays open. A Gap does not stop it at once: the loop
builds its Gaps in [one round](the-loop/drift-check.md#the-gap-round). A Gap still left after that round stops the loop.
Every ticket has landed by then, so there is nothing to Keep, and the full run still runs before the
loop ends. The line names each Gap left:

```
STOP  the drift check still finds 2 Gaps on spec #200 after the Gap ticket was built, and the loop goes round once. A person decides.
      Gap: S4 is Missing: No code writes the NOTE lines.
      Gap: The user docs has no Verdict
      Read it at .spec-loop/200/drift-gaps.md
```

The loop built these once and they are still owed, so a second build would most likely miss again.
Read the report, build what is owed in a ticket of its own or change the spec, and run the loop again.

**A Name report the loop cannot read.** After the drift check, the script runs [the Name
check](the-loop/name-check.md). No Name report, or a report with no `### Renames` list, stops the loop with
a `STOP` line, and the spec stays open. A rename does not stop it: the loop builds it in [the rename
ticket](the-loop/name-check.md#the-rename-ticket).

**A rename not made.** After the rename ticket Lands, [the Name re-check](the-loop/name-check.md#the-name-re-check) gives
each rename Done or Not done. A rename Not done, one with no Verdict, or one with two stops the loop.
So does a Name re-check that recorded no new report, or one with no `### Verdicts` list. The full
run still runs first. The line names each rename not made:

```
STOP  the Name re-check finds 1 rename not made on spec #200 after the rename ticket was built. A person decides.
      Not made: Batch is Not done: Batch is still the name in two files.
      Read it at .spec-loop/200/names-renames.md
```

The loop built the rename once and it is still owed. Make it in a ticket of your own, and run the loop
again.

### Restarting a stopped run: the Keep

To restart, run the same command again: `spec-loop <spec>`.

It first does a **Keep** on the worktrees the stopped run left behind. For each one, it commits any
uncommitted work to the Job branch, removes the worktree, and renames the Job branch out of the way,
to `spec-loop/<spec>/ticket-<n>-kept-1`. A Keep discards nothing. The log says what it kept:

```
KEPT  ticket-203 held uncommitted work. The whole attempt is on branch spec-loop/200/ticket-203-kept-1
```

**Held** means the worktree had uncommitted work, and the Keep committed it. **Clean** means it had
none. Either way, the attempt is on that branch if you want to read it.

Then the run starts the first open ticket again from the Target branch, with a fresh build.

### A Denial, and `--bypass`

A **Denial** is a tool call Claude Code turned down because the Session had no permission for it: a
write to a protected path, or a command no allow rule names. A Session with nobody watching cannot ask
you, so a Denial is final. A write under `.claude/` is always turned down in the default mode, whatever
your allow rules say.

Many Denials are worked around. When a step stops and its result lists Denials, the `FAIL` line names
each one and adds a hint. So does the `STOP` line of a Cut that filed no tickets, and of a check that
recorded no report:

```
      Denial: Write {"file_path": ".claude/settings.json", ...
      If one of these Denials stopped the loop, rerun with spec-loop 200 --bypass
```

The default mode is `acceptEdits`. `spec-loop <spec> --bypass` runs every Session of the run in
`bypassPermissions`, the landing too. Use it only when a Denial stopped the loop. A stop with no
Denials gives no hint, because its cause lies somewhere else. The `LOOP` line at the top of the log
names the mode the run is in.

The drift check and the Name check read the spec's commits through `spec-commits`, and record their
reports through `tracker-publish`. With no `Bash(spec-commits:*)` or no `Bash(tracker-publish:*)`
rule in your allowlist, that command is a Denial, and the loop stops at the check. Its `STOP` line
names the Denial, and a rerun with `--bypass` gets that one run past it. Add the rules with
`allow-commands` too, because every run after it in the default mode meets the same Denial.

## The stage map

Each stage of the loop reads some of your Steering. This map says which files, and where your team can
change what the stage does. [Steering](steering.md) has the detail on each file.

Two kinds of load:

- **Always** means the file is in the Session from its start. `CLAUDE.md` loads, and it imports the
  five rules in `docs/agents/rules/`: `comments.md`, `determinism.md`, `file-placement.md`,
  `testing.md` and `words.md`. The map calls these "`CLAUDE.md` and the rules".
- **On demand** means a skill reads the file only when that stage needs it.

`.claude/settings.json` applies to every Session too. Its allowlist decides which tools a Session can
use with nobody watching.

<!-- stage map -->
| Stage | Always loads | Loads on demand | What your team can change |
|---|---|---|---|
| The grill | `CLAUDE.md` and the rules | `domain.md`, your glossary, `docs/adr/`, `surfaces.md` | The glossary and the ADRs. The grill writes them as words and decisions settle. The Surfaces in `surfaces.md`, which decide what the grill asks once the design is settled. |
| The gate | The same Session as the grill | Nothing more | Nothing in a file. Your yes or no is the lever. |
| The spec | `CLAUDE.md` and the rules | `issue-tracker.md`, your glossary, `docs/adr/`, `surfaces.md` | The glossary and the ADRs, which give the spec its words and its decisions. The Surfaces in `surfaces.md`, which name the Surfaces section of the spec. |
| The tickets | `CLAUDE.md` and the rules | `issue-tracker.md` | "The ticket shape" in `issue-tracker.md`: the size of a ticket, its title and its sections. |
| `build` | `CLAUDE.md` and the rules | `domain.md`, your glossary, and `suite.json` when it runs `skillworks-suite` | The rules the change must meet, and the checks in `suite.json`. |
| `standards` | `CLAUDE.md` and the rules | `review-standards.md`, your glossary | The rules, and the smells, your checks and "Do not report" in `review-standards.md`. |
| `spec` | `CLAUDE.md` and the rules | `issue-tracker.md`, `surfaces.md`, `review-spec.md` | "The ticket shape" in `issue-tracker.md`, because the review judges the change by the ticket. The Surfaces in `surfaces.md`, which say where each Surface the spec names lives. Your checks and "Do not report" in `review-spec.md`. |
| `architecture` | `CLAUDE.md` and the rules | `domain.md`, your glossary, `docs/adr/`, `review-architecture.md`, `placement-checks.md` | `file-placement.md`, the failures, your checks and "Do not report" in `review-architecture.md`, and the commands in `placement-checks.md`. |
| `fix` | `CLAUDE.md` and the rules | Nothing more. It acts on the three reports. | The rules the fix must meet. |
| `sweep` | `CLAUDE.md` and the rules | Nothing more. `comments.md` is already loaded. | The keep and cut table in `comments.md`, and `doc-comments`. |
| `suite` | Nothing. No Session runs. | `suite.json`, and each Dockerfile a check names as its `image` | Every check, its `ready`, its `ignores`, its `image`, and `runs`. |
| `finish` | `CLAUDE.md` and the rules | `issue-tracker.md` | Nothing. The loop reads back the two conventions in `issue-tracker.md`, so leave them as they are. |
| Landing | `CLAUDE.md` and the rules, in the Session that resolves a conflict | `suite.json`, for the Suite again | The checks in `suite.json`. |
| The drift check | `CLAUDE.md` and the rules | `issue-tracker.md`, your glossary, `surfaces.md` | The glossary, which judges the names two tickets brought in. The Surfaces in `surfaces.md`, which say where each Surface the spec names lives. |
| The Gap ticket | What each step above loads, since it is built through them | The same as each step | Nothing in a file. The script writes it from a fixed template, out of the drift report's Verdicts and reasons. |
| The Name check | `CLAUDE.md` and the rules | `issue-tracker.md`, `CONTEXT-MAP.md`, your glossary | The glossary, which decides the word a moved name or a concept named two ways should take. |
| The rename ticket | What each step above loads, since it is built through them | The same as each step | The glossary, whose word each rename takes. The script writes the ticket from a fixed template, out of the Name report's lines. |
| The full run | Nothing. No Session runs. | `suite.json` | The checks in `suite.json`. |

The rules' settings load into every Session, but each one is enforced only once a check exists that
reads it. Until then, `build` and `fix` follow them as prose, and the reviews judge the change by
reading them. `suite` enforces a setting only when a check in `suite.json` reads it, and
`architecture` runs only the commands in `placement-checks.md`. `/skillworks:architecture-tests`
adds those checks.

| Rule | The settings a check enforces |
|---|---|
| `file-placement.md` | `slices`, `concerns`, `max-types-per-folder`, `source-files`, `test-files`, `skip-folders`, `banned-folder-names`, `name-map`, `test-roots` |
| `determinism.md` | `clock`, `contexts` |
| `words.md` | `banned-words`, `skip-folders` |
| `comments.md` | `doc-comments` |
| `testing.md` | None. No check reads it, so the `standards` review is its only judge. |

The steps, their order and what each one does are Machinery. They are the same in every repo, and no
file changes them. So this map lives here only, and setup copies no map into your repo.

## Reading a run

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
in place of the `SCOPE` line, as [When a step fails](#when-a-step-fails) shows.

The `COUNT` line says how many items the spec holds and how many Verdicts the report gave. A `NOTE`
line names each Unrequested item. A `WARN` line names a Verdict for an item the spec does not hold.

When the count finds a Gap, [the Gap round](the-loop/drift-check.md#the-gap-round) adds its lines before the full run's. A
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

When the Name check finds a rename, [the rename ticket](the-loop/name-check.md#the-rename-ticket) adds its lines before
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
with no commit to read, as [When a step fails](#when-a-step-fails) shows. It comes last, after the
full run's lines, in place of `END`. `END` comes only on [a clean finish](the-loop/full-run.md#a-clean-finish).

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
