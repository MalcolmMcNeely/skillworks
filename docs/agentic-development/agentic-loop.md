# The agentic loop

How a design becomes code in this repository. Two stages, and one gate between them.

Stage one is an interview. You argue the design out, and the words and decisions are written to the
repository as they settle. It ends when you confirm the design.

Stage two is a script. It breaks the design into tickets and drives each one to `main` on its own, in
a throwaway worktree, through a fixed run of Claude Code Sessions. Nobody watches it.

```
/grill-with-docs   →   you confirm   →   /spec-loop <spec#>   →   every ticket on main
     stage one            the gate              stage two
```

Your `yes` at the gate is the whole of your consent. Nothing between it and the drift report at the
end asks you anything.

## Stage one: settle the design

### /grill-with-docs

The skill runs two others on every round. `grilling` owns the questions. `domain-modeling` owns the
words.

The design is a tree: every decision branches into the decisions hanging off it. The **frontier** is
the set of decisions whose prerequisites are already settled, which is exactly the set of questions
that can be asked without guessing an answer nobody has given yet. Questions come one at a time, each
numbered and each carrying a recommended answer. Your answers push the frontier outward and unblock
the next round.

Finding facts is never your job. A frontier question that needs a fact from the tree or the tracker
goes to a sub-agent. Questions downstream of that sub-agent wait for it; the rest of the frontier is
asked now. The decisions are yours. The lookups are not.

`CONTEXT.md`, the glossary that claims the code, and `docs/adr/` are edited the moment a word or a
decision settles, not at the end. Every Session after this one starts with an empty context and can
only find those decisions in the repository.

### The one gate

When the frontier is empty the Session sums up the problem, the design, the words and ADRs written
along the way, and what was ruled out, then asks you to confirm.

On **no**, the frontier was not empty after all: what you said becomes the next round.

Say **yes** and everything afterwards runs unattended, which is why the summary is the thing you
consent to. It carries every decision the spec will be built from.

### /to-spec

On your yes, `/to-spec` runs. It publishes a `SPEC:` issue to the tracker with the `ready-for-agent`
label, commits and pushes whatever the interview changed on disk, and reports the spec's number.

The push matters as much as the issue. The spec points at decisions that must already be in the
repository, because no later Session can see this one.

That number is the argument to `/spec-loop`.

## Stage two: build it

### /spec-loop, the skill

Four steps, and only the last one speaks to you.

1. **Check the spec.** Read the issue in full. It must be open, because the loop needs it as the
   parent of its tickets. If it already has sub-issues, the breakdown has happened.
2. **Break it into tickets.** `/to-tickets` cuts the spec into tracer bullets: narrow slices that each
   go through every layer, each sized for one fresh context window, each declaring the tickets that
   block it. Every ticket is published as a **sub-issue of the spec**. That parentage is the only
   thing stopping two people's loops taking each other's work.
3. **Hand over to the driver.** Start `uv run scripts/spec_loop.py <spec>` in the background and say
   where the log is.
4. **Report.** When the script exits, read the log and say which tickets closed.

The skill is forbidden from implementing a ticket itself. If a model picks the next ticket, the choice
moves back inside a context window, which is the one thing this design exists to avoid.

Step 4 makes exactly one offer: close the spec. A clean finish takes two facts together, and the log
alone is not enough, because a drift check that found gaps still exits 0. The log must reach its `END`
line, **and** the drift comment on the spec must list nothing Missing, Partial or Contradicts.

### The driver

`scripts/spec_loop.py` holds the control flow. It is a script and not a prompt so that a run can be
read, stopped and resumed. A model can skip a step a skill asks for, so every step is a separate call
here. A step can exit 0 and do nothing, so the script reads a fact after each one.

**Before it starts** it checks that `gh` is installed and logged in, that `claude` is on `PATH`, that
the spec reads and is open, and that the spec has at least one sub-issue. Then it Keeps any worktree
group a stopped run left behind, fetches `origin`, and records `origin/main` in
`.spec-loop/<spec>/base.sha`. That file is written once and never rewritten, so a resumed run still
measures from where the first run began.

**Picking a ticket** is a query, not a judgement. The driver takes the spec's first open sub-issue
whose blocker count is `0` and that nobody else has claimed. If the tracker does not report a blocker
count at all it stops rather than guess.

**Claiming** it assigns itself, waits three seconds, then reads the assignees back. Another name
there means it unassigns itself and moves on. That detects a race; it does not prevent one.

**A worktree per ticket**, cut from the newest `origin/main`, under
`.claude/worktrees/spec-<spec>/ticket-<n>`. Your own checkout is never worked in, so you keep it, on
any branch, with any edits in it, for the whole run. A ticket that passes has its worktree and its
branch removed. A ticket that fails keeps both, so the broken state can be read.

### Seven Sessions per ticket

Each step is its own `claude -p` call, run inside the ticket's worktree, asked for JSON so the driver
can read the result.

| Step | What it runs | Session | Checks after it |
|---|---|---|---|
| `build` | `/implement <n> --stop-after-tests` | fresh, and its id is kept | no-error, command-loaded, ticket-open, tree-changed |
| `standards` | `/review-standards <n>` | fresh | no-error, command-loaded, ticket-open, axis-reported |
| `spec` | `/review-spec <n>` | fresh | no-error, command-loaded, ticket-open, axis-reported |
| `architecture` | `/review-architecture <n>` | fresh | no-error, command-loaded, ticket-open, axis-reported |
| `fix` | `/implement <n> --fix` | resumes `build` | no-error, command-loaded, ticket-open |
| `sweep` | `/comment-sweep` | fresh | no-error, command-loaded, ticket-open |
| `finish` | `/implement <n> --finish` | resumes `build` | no-error, command-loaded, new-commit, tree-clean, ticket-closed |

`build` leaves its change uncommitted. The three axes each read that change, report under a heading of
their own, and fix what they find. `fix` reconciles: it is the only step that holds all three reports
and all three records at once. `sweep` writes last, because every step that writes now runs after the
place the sweep used to sit, and each one could put back what it had just cut. `finish` runs the whole
suite, commits and closes the ticket. It never pushes.

### Which Sessions resume, and why

The `build` step's Session id is read out of its JSON result and carried forward. Three later calls
reuse it with `--resume`: `fix`, `finish`, and the conflict step during landing. The other four start
cold.

The split is the point rather than an economy. An axis that resumed the build Session would be marking
its own work, and the side it already understands would look right every time. Each axis runs with no
`--resume` so that none of them reads another's mind. The sweep runs cold too, and reading the change
cold it sees the whole ticket, where a sweep resumed in the build Session would only ever see what
that Session had written.

`fix` and `finish` resume because they act on the code the build Session wrote. Resuming means the
prompt only has to carry what is new.

The three reports never travel inside a Session. Each axis writes its report to disk, and the driver
reads all three back and builds the `fix` prompt **before** that Session starts. So a reconciling step
never runs on two axes out of three, and no Session has to remember to carry anything.

### What each axis changed

An axis may write, so an axis could write silently: a change the build Session never made, that no
report names, and that the closing step commits under a message written by someone who never saw it.

The driver takes a reading of the worktree immediately before each axis step and again immediately
after. The difference is what that axis changed. It reaches the log as an `EDITS` line and rides into
the `fix` prompt beside that axis's report.

The reading is of the bytes of every changed file, not of the file list, because an axis that edits a
line inside a file the build Session already changed leaves the file list identical. It is a record
and not a check: an axis that edits is doing its job, so nothing here ever stops the loop.

Ordering therefore matters. `standards` edits before `spec` and `architecture` read, so two more axes
see its work; `architecture` edits after every other axis has finished, so none of them do. `fix` and
the suite both run after all three, which is what makes that asymmetry affordable.

### The checks

A step can exit 0 and do nothing. So after every step the driver reads a fact, out of the step's
result, out of git, or off the tracker.

| Check | What it reads |
|---|---|
| `no-error` | The step's JSON says the Session did not end in an error. |
| `command-loaded` | The record the Session itself wrote, looking for the command tags in a user prompt. This proves the slash command expanded, rather than that a model talked about it. |
| `axis-reported` | The result holds that axis's own heading. A Session can end its turn having said nothing, so the heading is what proves it did not. |
| `ticket-open`, `ticket-closed` | The issue's state on the tracker. |
| `tree-changed`, `tree-clean` | Whether git reports anything uncommitted in the worktree. |
| `new-commit` | `HEAD` differs from what it was before the first step ran. |

### Landing

A ticket Lands the moment it passes, on its own, so a stopped run leaves every ticket before it
already on the remote. `scripts/land_ticket.py` does it, in six steps:

| Step | What it does |
|---|---|
| `verify` | The worktree is Clean, and every commit carries a `Ticket: #<n>` trailer. A commit without one could never be traced back. |
| `fetch` | Get `origin`, and check there is something left to land. |
| `rebase` | Onto the newest `origin/main`, but only when the base has moved. Then check no commit and no file was lost. |
| `resolve` | Only when the rebase conflicts. The build Session is resumed to fix it. |
| `suite` | The whole suite again, on the new base. An unmoved base is one the `finish` step's own run already answers for. |
| `push` | `HEAD` onto `main`, retried up to three times when another loop wins the race. |

The resumed conflict Session is told its own bias outright: you wrote one side of this and the other
side is a stranger, so argue for the other side before discarding a line of it. The driver hands it
the commits that landed while this ticket was being built, the ticket behind each one, and each of
those tickets' closing comments.

Nothing is pushed unless every step passes.

### When a step fails

The run stops at the first failure. It does not carry on and it does not try to rescue itself.

The driver reopens the ticket, because the loop only picks open tickets and the `finish` step may have
closed one whose work never reached the remote. The `FAIL` line names the worktree and the two files
to read: the step's result and its error output. The worktree and its branch stay where they are.

Running the same command again then refuses, because that worktree is still there, and the refusal
names the two ways out: carry on in the worktree, or throw it away with the command it prints. Once it
is gone, a rerun resumes from the first open ticket.

One stop is common enough to be named in every failure message: a write under `.claude/` is refused as
a sensitive file whatever the allowlist says. `SPEC_LOOP_PERMISSION_MODE=bypassPermissions` is the way
past it. The default is `acceptEdits`.

### The drift check

Every ticket passed its own acceptance criteria. Nothing so far has asked whether the pile of them is
what the spec wanted.

So the driver opens one last worktree and runs `/spec-drift <spec> <base>` in a fresh Session. It
classifies every user story and implementation decision as Done, Partial, Missing or Contradicts,
lists anything Unrequested, and looks for the failure no per-ticket check can see: two tickets that
introduced competing names for one idea, with the glossary as arbiter. It judges against the spec and
not against the tickets, because a ticket that drifted still passed its own criteria.

It posts a comment on the spec. It fixes nothing and closes nothing. A fix is new work and needs a
ticket of its own, and closing the spec is where a human declares the work done.

## Reading a run

The log is `.spec-loop/<spec>/loop.log`, and every step's result and error output sits beside it.

```
15:55:22 START #202 TICKET: Preflight checks for uv
15:55:32 STEP  #202 build        2/6
15:57:41 STEP  #202 standards    2/6
15:59:38 EDITS #202 standards    changed scripts/spec_loop.py
16:00:31 STEP  #202 architecture 2/6
16:02:18 STEP  #202 fix          2/6
16:29:54 STEP  #202 finish       2/6
16:56:48 ok    #202 landed on main as bfa44a6
16:56:52 DONE  #202  bfa44a6
16:57:06 STEP  #203 build        3/6  ~245m left
```

The position counts closed tickets rather than this run's, so a rerun starts at its real place. The
estimate is a mean of the tickets this run has finished, with the one now running counted as
remaining, so it never flatters the run.

Expect hours. On a six-ticket spec a build step ran between six and sixty-three minutes, and a ticket
took one to four hours end to end.

`--dry-run` prints the whole plan instead of running it: every ticket, the worktree and branch it
would get, every step's command line and checks, and the landing steps asked of `land_ticket.py`
itself. It starts no Session and reaches no remote.

## Where the pieces live

| Path | What it is |
|---|---|
| `.claude/skills/` | The skills each step calls. |
| `scripts/spec_loop.py` | The driver. Picks the ticket, runs the steps, reads the facts. |
| `scripts/land_ticket.py` | Gets one finished ticket onto `main`. |
| `scripts/ticket_worktree.py` | Makes, Keeps and removes the worktree a job is built in. |
| `.claude/CONTEXT.md` | The glossary for all of the above. Clean, Held, Keep, Land, Load, Runner and Session are defined there. |
| `docs/adr/` | Why the loop is shaped this way. ADR 0021 on landing each ticket as it finishes, ADR 0024 on the axes editing and the sweep running last, ADR 0025 on the driver being Python. |
| `.spec-loop/<spec>/` | What one run of that spec did. |
