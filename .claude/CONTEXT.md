# Loop

How an agent is steered in this repository, and how a session is watched. Studio is the app, and
Architecture is the shape Studio's code keeps. This context is neither: it is the setup an agent runs
under, and the scripts that drive it.

## Language

**Clean**:
A worktree git reports nothing uncommitted in. A Kept job is Clean when its branch carries only the
commits the job had already made, and the driver reads the same fact of a finishing worktree before
it lets a step pass. One word, because a job that stopped and a job that finished are asked the same
question.
_Avoid_: Pristine, unmodified

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

**Held**:
A worktree that had uncommitted work in it when the run stopped. A Keep commits that work to the
job's branch before the worktree goes, so Held says the branch carries work that reached no commit of
the job's own. Held is the case a Keep exists for, and Clean is the other one.
_Avoid_: Dirty, unsaved

**Keep**:
What the loop does to the worktree group a stopped run left behind. Each job's uncommitted work is
committed, its branch is renamed out of the way so the job can be opened again, and the worktree
goes. A Keep discards nothing, which is what lets one command restart a stopped run. Closing is its
opposite: a job that passed has its worktree and its branch both removed.
_Avoid_: Stash, salvage

**Land**:
A finished ticket reaching `main`. The driver rebases the ticket's worktree onto the newest `main`,
proves the work survived and the suite is green, then pushes. A ticket Lands on its own, the moment
it passes, so a stopped run leaves every ticket before it already on the remote.
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

**Runner**:
The one way the driver reaches another program. It is injected, so a test supplies its own rather
than putting a fake on `PATH`.
_Avoid_: Spawn, shell, executor

**Session**:
One run of Claude Code, from the first prompt to the last. It carries an identity that every Load and
every telemetry event of that run shares, which is what lets the two be read together.
_Avoid_: Conversation, chat, transcript

**Smart zone**:
The part of a context window in which a model still keeps every instruction it was given. A session
is planned to finish its work inside it.
_Avoid_: Context budget, token limit, sharp window

**Steering**:
What a repo tells the loop about itself: its rules, its tracker docs, its review baselines and its
Suite. Setup copies a starting version into the repo as files, and the team owns them from then on.
A skill reads a fact about one repo from its Steering and never carries it.
_Avoid_: Config, guidance, policy

**Suite**:
The checks a repo names for the loop to run before a ticket Lands. The repo owns the list, so each
team says what green means for its own code. A Suite ends one of two ways that are never confused: it
went red, and the ticket goes round again, or the machine was not ready to run it, and the loop stops.
_Avoid_: Test run, pipeline, CI

**Turn**:
The right to push to `main`, held by one loop at a time in one clone. A loop that lost a push race
waits for its Turn and holds it until it Lands, so the loops beside it cannot beat it again. A loop
that has not lost takes its Turn only for the push. A Turn orders the loops of one clone and no
others: a push from anywhere else can still beat it, and the loop tries again.
_Avoid_: Lock, mutex, queue
