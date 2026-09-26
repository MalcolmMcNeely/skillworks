# A Session that stops short is Nudged by the driver

A step whose Session ends with work still owed is resumed by the driver with a Nudge, at most twice,
before the loop stops. A check that proves the work was done earns a Nudge: a review's heading, a
build that changed the tree, a finish that committed, left the tree Clean and closed the ticket. A
check that proves the Session could run does not, because carrying on cannot mend a Session that
errored, loaded no command, or found its ticket closed. The Nudge names each check that failed, says
that any command the Session left in the background was stopped with its last turn, and asks it to
say what blocks it if something does.

Every Session also runs with a Bash limit of 45 minutes, by default and at most, so a long command
finishes in the foreground.

## Why a step stopped short

An architecture review ran the Python script tests with the highest limit it could ask for, ten
minutes. They take 17 and a half. Claude Code moved the command to the background and told the
Session it would be notified when it ended. Under `claude -p` nothing notifies: the process kills
its background shells about five seconds after the last result. The Session said it would wait,
ended its turn, and never wrote its report. The heading check stopped the loop, correctly, and a
finished build and two passed reviews went to a Kept branch. The morning's run hit the same limit
and passed only because that Session read the output file instead of waiting.

Anthropic's guidance for unattended runs of Opus 5.5 names the pattern: an agent can end its turn
with a report while work is still owed, so a harness treats that end as a report, names what is
still open, and stops after two or three continuations.

## Considered options

**A Stop hook in each Session.** Rejected. It moves a gate back inside the Session, which ADR 0026
took out, and the driver keeps its own check beside it, so one fact is checked twice. It only runs
inside a real Session, so no deterministic test can prove it. A blocked stop brings back no output
from a background command, and Claude Code ends the turn after eight blocks, which a Suite that runs
for many minutes can use up. It would earn its place if background shells came back despite the
raised limit, because it is the one option that acts before `claude -p` kills them.

**Turn off background tasks with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`.** Rejected. It is a switch
Claude Code offers, not something Anthropic advises, and it takes away running two long checks at
once. The raised limit removes the cause, and the Nudge catches a Session that backgrounds something
and stops anyway.

**Nudge only a review that wrote no heading.** Rejected. A build is the most expensive step to lose,
and it can stop short the same way.

## Consequences

A Nudged step takes longer, and the log says so. A command that hangs holds its step for up to 45
minutes before the Session hears of it.

The architecture review runs only the commands the placement-checks file names, not the Suite. The
driver runs the whole Suite as its own step, so the review was running tests it never read.
