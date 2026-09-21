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

**Runner**:
The one way the driver reaches another program. It is injected, so a test supplies its own rather
than putting a fake on `PATH`.
_Avoid_: Spawn, shell, executor
**Session**:
One run of Claude Code, from the first prompt to the last. It carries an identity that every Load and
every telemetry event of that run shares, which is what lets the two be read together.
_Avoid_: Conversation, chat, transcript
