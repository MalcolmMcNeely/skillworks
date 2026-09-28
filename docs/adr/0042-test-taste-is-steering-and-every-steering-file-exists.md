# Test taste is Steering, and every Steering file exists

`tdd` held a team's taste in tests, and read no Steering: what to mock, which fake library, one
assertion per test, test names, and integration style over unit style. A change to that taste had to
reach the skill as well as a team's rule, and a team could not edit it. So the taste moves to a new
rule, `docs/agents/rules/testing.md`, and its Seed carries today's words. `tdd` keeps the method:
red before green, vertical slices, tests at seams through public interfaces, and the anti-patterns.
The test-first loop stays Machinery. `tdd` states its seams and goes on, and never waits for a yes.
The Fakes section leaves the determinism rule for the testing rule, so mocking lives in one place.

`tdd` stops when the testing rule is missing, as `comment-sweep` stops without the comments rule. So
every Steering file always exists. Setup writes each missing one, even a file the team deleted, and
a team that wants less of a file empties it down. The loop's preflight stops before any ticket runs
when a file setup seeds is missing, and it reads the same list `seed-steering` writes from.

## Considered options

**Test-first becomes a lever.** Rejected. The loop's quality rests on red before green, and ADR 0038
already turned down making every opinion a lever.

**The taste goes in an on-demand file that only `tdd` reads.** Rejected. It costs less, because a rule
loads into every Session. But the fix step writes tests without calling `tdd`, and a rule reaches
every step that writes a test.

**`tdd` goes on with the method alone when the rule is missing.** Rejected. A missing rule means setup
has not run since the rule joined the Seeds, and the fix is to run it. A skill that quietly drops the
team's taste hides that.

**A deleted Steering file stays deleted.** Rejected. A step that needs the file would then stop in the
middle of a ticket, and setup could never repair it.

**A `fakes` setting names the fake library.** Rejected for now. No check reads it, so it would only be
prose in another place. A setting joins the day a check needs one.

## Consequences

A Plugin update reaches a team before its Steering does. Until the team runs setup again, the loop
stops at its preflight with a message that says to run setup. It never stops in the middle of a
ticket.

This replaces one line of ADR 0038's Machinery list. The test-first loop in `tdd` stays there, and
the taste in tests leaves it.
