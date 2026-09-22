# The driver runs the suite, and a red one goes round once

The suite is the gate that says a ticket is done, and it was the one gate resting on a session's
word. `finish` ran the tests inside a Session and the driver read only whether a commit appeared and
the ticket closed. Nothing said what `finish` should do when the suite went red, so a Session fixed
it, committed, and passed every check the driver had, carrying comments no sweep ever saw. The
driver now runs the suite as a step of its own and holds the result.

The loop runs eight steps:

```
build → standards → spec → architecture → fix → sweep → suite → finish
```

`suite` proves the tests can run, runs them, and keeps the output. `finish` no longer runs tests: it
commits and closes, and is handed the passing output for the closing comment.

A red suite sends the loop back to `fix`, once, with the failure text in the prompt. The way back
runs `fix → sweep → suite`, never `fix → suite`, because `fix` writes and a sweep has to follow the
last writer. Still red after that one circuit and the loop stops, leaving the worktree.

Two things guard what "red" means, because one word was hiding four different failures. A test
failed, the suite would not build, the suite could not start, and a flake all arrive as the same
non-zero status, and only two of the four are the ticket's fault. Before it runs anything, `suite`
proves the tests *can* run — Docker up, `uv` present, `node_modules` in place. A precondition that
fails stops the loop and is never handed to a Session, because no Session can start Docker. And a red
suite is run a second time before it is believed, because the container-backed Span tests flake here
and a Session handed a failure it cannot reproduce may weaken a test or edit code that was never
broken.

## Considered options

**`finish` stops on a red suite, and never fixes.** The cheapest answer, and the strongest guarantee:
nothing can write after the sweep, ever. Rejected because the loop should fix what it has the
information to fix. Stopping an overnight run at step seven of eight, on a failure the Session that
wrote the code could read and correct, spends a developer to save a driver.

**`finish` fixes the red suite and sweeps its own change before committing.** The obvious answer, and
the one to reach for first. Rejected by the rule [ADR 0024](0024-a-review-axis-edits-and-the-sweep-follows-the-last-writer.md)
already holds: a step written into a skill can be skipped, and a step in the script cannot. The sweep
guards a rule, so a second sweep asked for in a skill guards nothing.

**`finish` keeps running the suite and says it went red.** The driver reads the Session's result and
decides from that. Rejected twice over. The driver would learn the gate's answer from the Session it
is checking, and the failure text would have to survive a Session that has ended. The text is the
whole reason the retry can work.

**The driver tells the four failures apart by reading the runner's output.** Rejected. It means
parsing text that changes with every version of `dotnet test` and pytest. Whether Docker is running is
a fact, and a fact is what settles it.

**The first red is red.** One fewer suite run. Rejected because a flake then spends the single
circuit, and hands a Session a failure that is not there.

**Two circuits rather than one.** Rejected. The retry is not a blind second attempt: `fix` resumes the
build Session and is handed the failure text, so a Session with the whole ticket in hand has already
tried and failed. A third is unlikely to differ, and an unattended run wants a bound small enough to
hold in your head.

## Consequences

This replaces the step list in ADR 0024, and nothing else in it. Its rejected options stay the record
of why the sweep is a step in the script rather than a line in a skill, and that rule is what decided
two of the options above.

`land_ticket.py` still runs the suite after a rebase, for its own reason: proving the work survived a
base that moved. Both callers share one way of running it, so the preconditions and the command list
cannot disagree.

The step list lives in `STEPS` and in two documents. A test now reads `STEPS` and holds both to it,
because a document that can silently contradict the script is the same defect one layer out.

Fixing no longer covers review findings alone. A prompt carrying a failing suite has that to fix, and
the section says so. The flag does not change: the retry is `--fix`, because it is the same act on a
different input.
