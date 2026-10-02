# Loop

How an agent is steered in this repository, and how a session is watched. Studio is the app, and
Architecture is the shape Studio's code keeps. This context is neither: it is the setup an agent runs
under, and the scripts that drive it.

## Language

**Blocked**:
A step whose Session says, in the first line of its report, that the step owes work only a person
can clear. A Denial can be the cause, and so can a choice or a check that is a person's to make. It
is the Session's own word, so the driver reads it and does not judge it. A ticket that waits on
another ticket is not Blocked: it has an open blocker.
_Avoid_: Stuck, walled, refused

**Clean**:
A worktree git reports nothing uncommitted in. A Kept job is Clean when its Job branch carries only
the commits the job had already made, and the driver reads the same fact of a finishing worktree
before it lets a step pass. One word, because a job that stopped and a job that finished are asked the same
question.
_Avoid_: Pristine, unmodified

**Closing note**:
What a ticket carries when it closes: what was done, the checks that proved it, and the findings left
as they were and why. It is the richest record of intention the loop keeps, and a Session resolving a
conflict reads it back. On GitHub it is the comment the ticket closes with, and with files it is a
section of the ticket's own file, so one word serves both Trackers.
_Avoid_: Closing comment, close comment, resolution

**Cut**:
The step the driver takes before the first ticket, when a spec has none: a Session that breaks the
spec into tickets. It runs once for a spec and never for a ticket, so it is not one of the steps a
ticket takes.
_Avoid_: Ticket step, tickets step, breakdown

**Denial**:
A tool call Claude Code turned down because the session had no permission for it: a write to a
protected path, or a command no allow rule names. A session with no human cannot be asked, so a
Denial is final. Many Denials are worked around. One that stops a step is the case for running the
loop again in bypass mode.
_Avoid_: Refusal, wall, block

**Dev loop**:
The Grill, then the spec loop: the two stages a developer starts, one command each, to take an idea
to work that has landed. A stage of the Dev loop names only the next stage. Every other skill stays
open to a developer who types it, and the Dev loop never asks for one.
_Avoid_: Rail, main flow, happy path

**Drift check**:
The judge that gives each story, decision and Surface of a spec a Verdict once every ticket has
Landed. A Verdict judges the Target branch as it stands, so work that reached it by any way counts.
What nobody asked for is looked for only in the commits the spec's tickets Landed. It judges
against the spec and not the tickets, because a ticket that drifted still passed its own criteria.
It fixes nothing: the loop builds the Gaps it finds.
_Avoid_: Audit, acceptance check, final review

**Dumb zone**:
The part of a context window past the Smart zone. A model there does not fail loudly. It leaves out
an instruction, a constraint or the middle of what it read, and still sounds sure, so the error is
something missing and is easy to miss. Too many constraints push a model into it sooner.
_Avoid_: Degradation, drift, forgetting

**Edit**:
What a review axis changed in the worktree, as the driver read it and not as the session said it. The
driver takes a reading before the step and another after, and the difference between them is the
Edit. It is a record and never a judgement: an axis that edits is doing its job, so no Edit stops the
loop. What an Edit cannot be is silent.
_Avoid_: Record, change, diff

**Flake**:
A check that went red on one run of a Suite and passed on a later run of the same Suite, on the same
inputs. Nothing changed between the two, so the red was not the code's. A Flake counts as green, and
it is always reported, with its red output kept, so a check that flakes is never silent.
_Avoid_: Flaky test, intermittent, retry

**Fresh**:
A Session that starts with nothing in its context but what it Loads and what its prompt says. Its
opposite is a resumed Session, which carries on with all it already read and did. A Fresh Session
judges work it has no memory of writing, and starts in the Smart zone.
_Avoid_: Cold, blank, new

**Gap**:
An item of a spec the finished work does not yet deliver: a story or a decision the drift check found
Missing or Partial, or did not judge exactly once, or a Surface it found Out of step. The loop builds
its Gaps itself, in one ticket, once. A Gap still open after that stops the loop.
_Avoid_: Shortfall, hole, miss

**Grill**:
The stage where a developer and Claude argue a design out until nothing is left open, writing the
glossary and the ADRs as each settles, and ending in a published spec. The developer's yes to its
summary is the one gate before the spec loop runs with nobody watching.
_Avoid_: grill-with-docs, interview, design session

**Held**:
A worktree that had uncommitted work in it when the run stopped. A Keep commits that work to the
Job branch before the worktree goes, so Held says the Job branch carries work that reached no
commit of the job's own. Held is the case a Keep exists for, and Clean is the other one.
_Avoid_: Dirty, unsaved

**Hidden skill**:
A skill Claude never sees, so it never suggests it and cannot start it through the Skill tool. A
developer or the driver types it. The two stages of the Dev loop are hidden, and so are the steps the
driver types, so Claude can never send a developer off the Dev loop.
_Avoid_: Entry point, manual skill

**Keep**:
What the loop does to the worktree group a stopped run left behind. Each job's uncommitted work is
committed, its Job branch is renamed out of the way so the job can be opened again, and the worktree
goes. A Keep discards nothing, which is what lets one command restart a stopped run. Closing is its
opposite: a job that passed has its worktree and its Job branch both removed.
_Avoid_: Stash, salvage

**Job branch**:
The branch one job works on in its own worktree, cut from the newest Target branch. It goes with the
worktree when the job passes. A Keep renames it out of the way, and it is still a Job branch after.
_Avoid_: Ticket branch, work branch, feature branch

**Land**:
A finished ticket reaching its Target branch. The driver rebases the Job branch onto the newest
Target branch, proves the work survived and the suite is green, then pushes. A ticket Lands on its
own, the moment it passes, so a stopped run leaves every ticket before it already on the remote.
_Avoid_: Integrate, integration

**Load**:
One instruction file reaching a session. It names the file, where it came from, when it came and why.
A Load is a fact about a session, never a judgement: a file that arrives when it should not have
still Loads. A memory file Claude Code wrote is a Load like any other. Its source is the machine and
not the repository, so two machines can Load different files at the same commit.
_Avoid_: Arrival, injection, attachment

**Machinery**:
What the Plugin runs and no team edits: the skills, the scripts they drive, the hooks and the output
style. It runs from the Plugin, so every repo runs the same code and one update reaches them all.
_Avoid_: Engine, tooling, framework

**Name check**:
The judge that reads the commits a spec's tickets Landed against the glossary once the Gaps are
built, and lists each name whose meaning moved and each concept that two tickets named two ways. A
name that another spec or a person brought in is not its to judge. The loop makes every rename it
lists, in a ticket of its own, and never asks whether to.
_Avoid_: Rename check, naming review, lint

**Nudge**:
What the driver sends to resume a Session whose step ended with work still owed. It names what is
owed, so the Session carries on with its context rather than starting again. A Nudge answers a
Session that stopped short, never one that could not run, and a step that still owes work after two
of them stops the loop.
_Avoid_: Continuation, retry, prod

**Order of events**:
The order in which a test and the code it runs do things. It has to come out the same on a busy
machine as on a quiet one, so a test that acts while the code runs first waits on a fact that shows
the code is where the act needs it.
_Avoid_: Ordering, interleaving, timing

**Proof**:
A check that passed on one exact set of its inputs, kept by the Suite. A check whose inputs match a
Proof is not run again, so work already proved costs nothing a second time. A Proof knows only what
is in the repository, so a change outside it, such as a new SDK, can leave one stale. The full run
after each loop run that landed a ticket trusts none, and a check red there loses its Proofs. A Proof
belongs to one clone and never leaves it.
_Avoid_: Cache, memo, result, receipt

**Runner**:
The one way the driver reaches another program. It is injected, so a test supplies its own rather
than putting a fake on `PATH`.
_Avoid_: Spawn, shell, executor

**Seed**:
The Plugin's starting version of one Steering file. Setup copies it into the repo, and keeps a copy of
the Seed it copied beside it, so a later run can tell the team's edits from a Seed that moved on.
_Avoid_: Template, default, stub

**Session**:
One run of Claude Code, from the first prompt to the last. It carries an identity that every Load and
every telemetry event of that run shares, which is what lets the two be read together.
_Avoid_: Conversation, chat, transcript

**Smart zone**:
The part of a context window in which a model still keeps every instruction it was given. A session
is planned to finish its work inside it.
_Avoid_: Context budget, token limit, sharp window

**Steering**:
What a repo tells the loop about itself: its rules, its tracker docs, its review files and its
Suite. Setup copies a starting version into the repo as files, and the team owns them from then on.
A skill reads a fact about one repo from its Steering and never carries it.
_Avoid_: Config, guidance, policy

**Suite**:
The checks a repo names for the loop to run before a ticket Lands. The repo owns the list, so each
team says what green means for its own code. A Suite ends one of two ways that are never confused: it
went red, and the ticket goes round again, or the machine was not ready to run it, and the loop stops.
_Avoid_: Test run, pipeline, CI

**Surface**:
One place a change can have to reach besides the code that does the work, such as the docs, a public
API or a sample app. A team lists its own, and the grill asks about each one a change touches, so no
Surface is left out of step without anyone deciding it.
_Avoid_: Axis, touchpoint, artefact

**Target branch**:
The branch a ticket Lands on. It is `main` for a team that pushes straight to it. For a team that
reviews each spec as one pull request, it is that spec's own branch.
_Avoid_: Runway, trunk, base branch

**Tracker**:
Where a repo keeps its specs and tickets, and their state: GitHub Issues, or files committed under
`.specs/`. The loop reads what is open, blocked and claimed from it, so a ticket's state has to be
something every loop and every teammate sees.
_Avoid_: Backlog, board, issue store

**Trial**:
A run of some of a check's tests, where that check runs, so a Session tries its work without the
wait of the whole check. It proves nothing: it keeps no Proof, and the loop never reads it.
_Avoid_: Spot check, narrow run, focused run

**Turn**:
The right to push to the Target branch, held by one loop at a time in one clone. A loop that lost a
push race waits for its Turn and holds it until it Lands, so the loops beside it cannot beat it again. A loop
that has not lost takes its Turn only for the push. A Turn orders the loops of one clone and no
others: a push from anywhere else can still beat it, and the loop tries again.
_Avoid_: Lock, mutex, queue

**Verdict**:
A judge's call on one item, written as one line the driver reads: Done, Partial, Missing or
Contradicts for a story or a decision, In step or Out of step for a Surface, and Done or Not done for
a rename. The judge makes the call and the driver only counts, so an item with no Verdict is a Gap
and never a pass.
_Avoid_: Mark, grade, status

**Visible skill**:
A skill Claude sees, so it can suggest it and start it through the Skill tool. The opposite of a
Hidden skill, and it says nothing about what the skill does: a step of the Dev loop can be visible,
as `to-spec` is, because another skill calls it.
_Avoid_: Engine, tool, model-invocable skill
