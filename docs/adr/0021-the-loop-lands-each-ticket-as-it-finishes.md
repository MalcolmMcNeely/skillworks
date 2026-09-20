# The loop lands each ticket as it finishes

The spec loop worked in the one checkout and pushed once at the end. Both cost more than they bought.
The working tree was dirty with a half-finished ticket for the whole run, so while an hour-long loop
went the developer could not read a file without seeing its edits, could not try anything, and could
not start a second loop. And a spec that stopped on its eighth ticket left seven finished tickets on
one machine.

So each ticket is built in a throwaway worktree of its own, branched from the newest `origin/main`,
and lands on `main` the moment it passes. The worktree goes when the ticket passes and stays when it
fails, so a broken state can be read. The main checkout stays clean for the whole run, and two loops
on two specs can work at once.

## What this replaces

The driver stated a rule of its own: the loop commits per ticket and pushes once at the end, so a
half-finished spec never reaches the remote. This decision takes it away, and a reader who later finds
that rule gone should find this page.

This page landed before the code that leans on it, which is the order the work was planned in. The
rest of that work has since arrived. `scripts/spec-loop.sh`, `.claude/skills/implement/SKILL.md` and
the README now say what this page says, and none of them states the old rule any more.

It went because what it protected was not worth what it cost. It treated the spec as the thing that
has to be whole, and the spec is not: a ticket is. A ticket that has passed its review and the full
suite is finished work, and finished work sitting on one machine is work at the mercy of that machine.
The rule also made undoing a run a single `git reset --hard`, which is a convenience for the rare
abandoned run, paid for on every run that succeeds.

The thing that must be whole is now the ticket, and the checks that say so run before its push. The
rebase is verified by command rather than by asking the agent how it went, the full suite is re-run
whenever the base moved, and a push that lost a race is retried a bounded number of times.

## It refuses rather than guesses

Rebasing per ticket means meeting the commits that landed while the ticket was being built. The
session that wrote the ticket resolves that conflict, because half of it is already in its head, and
the driver hands it the other half: the commits, the ticket behind each one, and each of those
tickets' closing comments. Gathering all of that first is what makes a refusal honest. An agent can
only say the answer is in neither ticket once the tickets were in front of it.

It refuses in two cases. The answer is in neither side and in neither ticket. Or the project's checks
are still failing after one attempt to fix them. A refusal leaves the conflict alone, says which side
wanted what, and stops. It never means resolve badly.

A refusal stops the whole loop. The developer chose that over parking the ticket and carrying on,
because every stop says something about how to improve the loop, and a parked ticket is a stop nobody
sees.

## The two conventions the lookup rests on

A loop commit names its ticket, in a form that does not close the issue, and a ticket is closed with a
comment naming the commit. `docs/agents/issue-tracker.md` states both, because the resolution above
reads a commit message to find its ticket and reads that ticket's closing comment to find the
intention behind it. Neither may lapse.

Closing with a comment is already the habit. Naming the ticket is already the habit too, but not in a
form this can use: the commits before this decision say `Closes #n`, and GitHub's closing words close
an issue with no comment. The closing comment is the richest source of intention in this repository,
so the word that deletes it is the word that goes.

## Considered options

**Take the worktree and keep the one push.** Rejected. Freeing the checkout is the larger win, but
keeping the late push makes it worse rather than better: the finished work would then sit on a branch
nobody is looking at as well as on one machine. The worktree is also what makes the per-ticket push
cheap, because the rebase it needs is already happening.

**Park a failed ticket and carry on.** Rejected. It trades a stop the developer sees for one they do
not, while the loop is still new enough that every stop is worth reading.

**Limit the size of a conflict an agent may attempt.** Rejected. The published threshold comes from a
narrow 2020 model, and because a refusal stops the whole loop, refusing early saves nothing that
failing later would not also cost. Each conflict's size and outcome is logged instead, so a threshold
can later be set from this repository's own numbers.

**Hold a lock across integration.** Rejected. The lock would be held across a full test run, blocking
the other loop for minutes to prevent a collision lasting seconds. A rejected push costs less, and the
bounded retry already answers it.

**Close the ticket from the commit message.** Rejected. It is one fewer call, and it closes the issue
with no comment. The closing comment names the files touched, the tests run, and the findings the
agent chose not to fix with its reasons, and it is what a resolving agent reads. A convention that
deletes it to save a call is the wrong trade.

## Consequences

`git reset --hard` no longer undoes a run. Finished tickets reach the remote as they pass, so undoing
one is a revert like any other change that landed.

Every loop commit gains a trailer naming its ticket. That trailer is the whole of the commit-to-ticket
lookup, and it costs nothing to read. Counted across this repository's history up to this decision,
about two commits in five could be traced from the message at all, and the habit had been lapsing.

Older commits stay untraceable. The convention makes every future loop commit traceable, and the past
is left as it is.

A ticket reaches `main` before the spec's drift check has run. The drift check and the close offer are
unchanged, so what "done" means has not moved, but a ticket the drift check later questions is already
pushed. Answering it is a new commit rather than an edit to work still sitting at home.
