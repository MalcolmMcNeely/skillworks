# A red that did not change is not run again, and only the driver runs the whole Suite

On a .NET repo with one slow check over the whole solution, running tests took 76% of three spec
runs, and about 300 of 741 minutes repeated a result the loop already had. Three things change, and
none of them changes which checks run.

**A red check whose inputs did not change is red again, with no run.** The driver keeps the key of
each check that went red at a ticket's Suite step. At that ticket's next Suite step, a red check with
the same key is reported red, with its earlier output, and is not run. One ticket spent 83 minutes on
four runs of the same red after a `fix` Session that changed nothing. The red is held by the driver
for the one ticket and is never written to disk, so a red that came from the machine, such as Docker
going away, does not stick after the ticket.

**Under the loop, no Session runs the whole Suite.** Every Session is told to run only the tests near
its work, as a Trial, and the driver's Suite step is the one whole run. The sweep follows the last
writer, so it always edits after the Sessions, and any edit changes a check's key. A Session's
passing run therefore never stood in for the Suite step, and about 80 minutes of them were thrown
away. Review Sessions read the Suite text in their prompt as leave to run it, and did. A hand run of
`implement` still runs `skillworks-suite`, because no driver runs it there.

**A check may name a Rerun.** On the runs after the first, a red check runs its Rerun in place of its
whole command, so a flake in one test costs that test and not the whole check. The team's command
finds the tests that went red, so the Machinery still reads no runner output, as
[ADR 0026](0026-the-driver-runs-the-suite-and-a-red-one-goes-round-once.md) asks. Red and then green
on the Rerun is a Flake, as before. A check with an `image` cannot name one, because it runs on a copy
of the files and the first run's record of what went red is gone.

## Considered options

**The Suite keeps a red on disk, beside the Proofs.** Every run would read it, a Session's and a
developer's too. Rejected: a red from the machine would stay red on the same inputs, and a way to
clear it would be needed.

**Sweep before any Session that may run the Suite.** Rejected: build, the review axes and `fix` all
write, and the sweep follows the last writer
([ADR 0024](0024-a-review-axis-edits-and-the-sweep-follows-the-last-writer.md)).

**Keep a Proof through an edit to comments alone.** Rejected: it needs a reader of comments for every
language a repo holds.

**Only build keeps the whole Suite.** Build would see a break early. Rejected: the sweep still edits
after it, so the run is still lost time. A break build would have seen now spends the one red
circuit, and `fix` gets the failure text, which is what the circuit is for.

## Consequences

This replaces the line in [ADR 0039](0039-the-suite-keeps-proofs-and-a-check-names-what-it-ignores.md)
that an agent in the loop may run the Suite and its Proofs count for the driver. Proofs still count
wherever they come from.

With `runs` at 1, a check that flakes once, after a `fix` Session that changed nothing, stops the
loop, because its key did not change. With `runs` at 2, a check is red again with no run only after
it went red on both runs.
