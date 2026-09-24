# A loop that lost a push race lands on its Turn

A loop that loses a push race waits for its Turn, the right to push to `main` that one loop in a
clone holds at a time, and keeps it until it Lands. Every push takes the Turn. A loop that has not
lost holds it for a few seconds, only for its push. A loop that lost holds it from fetch to push, with
the Suite inside, so the loops beside it wait at their push and cannot beat it again. A lost race is
tried again for as long as it takes, because another loop pushing is an expected event and not a
failure.

## What this replaces

ADR 0021 rejected holding a lock across landing: the lock would block the other loop for minutes, to
prevent a collision of seconds, and a bounded retry already answered a lost push. The logs later
proved the retry did not. A lost push costs a whole Suite run, 13 to 34 minutes here, and one loop
landed inside that window every time. Two landings each rebased three times, passed the Suite three
times, lost three times and stopped their loops. Not one landing across this repository's loop logs
met a conflict, so the time went on Suite runs and never on fixing anything.

## Considered options

**Hold the Turn for every landing.** Rejected. A loop with no race to lose would wait on a loop that
lost, and most landings meet no race.

**Let a loop that has not lost push without the Turn.** Rejected. It pushes while the holder runs its
Suite, and the holder loses again. That is the failure the Turn exists to stop.

**One lander that takes tickets from a queue.** Rejected. The next ticket of a spec often needs the one
before it on `main`, so the loop waits all the same.

**Skip the Suite after a clean rebase.** Rejected. A rebase with no conflict can still break the program.

**A GitHub merge queue.** Rejected. It needs pull requests, and this repository has none.

**A Turn that every clone shares.** Rejected. The races seen were between loops of one clone, and the
retry still lands work that a push from somewhere else beat.

## Consequences

A Suite that hangs inside a landing holds the Turn until someone kills its loop, and every other
loop of the clone waits at its push. A loop that waits says which spec and ticket hold the Turn, so
the hang is found. The Turn is let go when the loop that held it ends, however it ends.

Only a lost race is tried again without end. Any other push error stops the loop at once, because a
person has to fix it.
